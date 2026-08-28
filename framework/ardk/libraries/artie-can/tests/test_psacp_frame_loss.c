/**
 * @file test_psacp_frame_loss.c
 * @brief Test that a multi-frame PSACP message damaged in transit is dropped, never delivered short.
 *
 * PSACP has no ACK and no retransmission, so a lost fragment cannot be recovered - the whole point
 * of the fragmentation scheme is that every way a message can be damaged is *detectable*, so a
 * subscriber can trust that what it receives is exactly what was published. These tests are what
 * pin that down, one per failure mode:
 *
 * - an interior PUB_MORE lost, or frames reordered -> the fragment index does not match
 * - the *last* PUB_MORE lost                       -> fewer PUB_MOREs arrived than PUB_START promised
 * - PUB_START lost                                 -> a continuation arrives with no slot open
 * - PUB_END lost                                   -> the slot ages out, or the next PUB_START reclaims it
 *
 * The tail-loss case is the one the design turns on. PUB_END carries no fragment index, so without
 * the count byte PUB_START spends on it there would be nothing to compare against: the receiver
 * would append PUB_END's payload where the lost frame's bytes belonged and hand the application a
 * message 8 bytes short, with no error. That is the failure this whole file exists to rule out.
 *
 * Like test_bwacp_frame_loss.c, these use a synchronous in-process bus rather than the UDP
 * multicast backend, so that a specific frame can be dropped deterministically, and drive a virtual
 * clock so that the reassembly timeout elapses in a few milliseconds of wall time.
 */

#include <stdio.h>
#include <string.h>
#include "unity.h"
#include "artie_can.h"
#include "util.h"

/** Node 1 publishes; node 2 subscribes. */
#define NUM_NODES 2

/** Topic used throughout, inside the protocol's valid 0x0B-0xF4 range. */
#define TOPIC 0x0CU

/** Index of the subscribing node in the arrays below. */
#define SUBSCRIBER 1

/** Upper bound on virtual time for a single exchange, comfortably past the reassembly timeout. */
#define MAX_VIRTUAL_MS 5000

static artie_can_context_t _contexts[NUM_NODES];
static artie_can_backend_t _handles[NUM_NODES];

/** Virtual clock. One round of ticks across all nodes advances this by 1 ms. */
static uint64_t _virtual_time_ms = 0;

static uint64_t _get_virtual_ms(void)
{
    return _virtual_time_ms;
}

/** Frame type to drop on the way to the subscriber, or 0xFF to drop nothing. */
static uint8_t _drop_frame_type = 0xFFU;
/** Which frame of that type to drop, 1-based. 0 means "every one of them". */
static uint32_t _drop_nth = 0;
/** How many frames of the target type have been offered to the subscriber so far. */
static uint32_t _frames_of_type_seen = 0;
/** How many frames were actually dropped, so a test can assert its injection really happened. */
static uint32_t _frames_dropped = 0;

static artie_can_error_t _bus_init(artie_can_context_t *context)
{
    (void)context;
    return ARTIE_CAN_ERR_NONE;
}

static artie_can_error_t _bus_close(artie_can_context_t *context)
{
    (void)context;
    return ARTIE_CAN_ERR_NONE;
}

/**
 * @brief Deliver a frame to every node except the sender, honouring the configured drop rule.
 *
 * psacp_receive_in_isr() does its reassembly inline, so delivering synchronously here is exactly
 * what a real receiver's interrupt would do with the frame.
 */
static artie_can_error_t _bus_send(artie_can_context_t *context, const artie_can_frame_t *frame)
{
    uint8_t frame_type = (uint8_t)((frame->id & ARTIE_CAN_FRAME_ID_FRAME_TYPE_MASK) >> ARTIE_CAN_FRAME_ID_FRAME_TYPE_LOCATION);

    for (int i = 0; i < NUM_NODES; i++)
    {
        if (&_contexts[i] == context)
        {
            continue; // Nodes ignore their own frames
        }

        if (frame_type == _drop_frame_type)
        {
            _frames_of_type_seen++;
            if ((_drop_nth == 0U) || (_frames_of_type_seen == _drop_nth))
            {
                _frames_dropped++;
                printf("  [bus] dropping frame type 0x%02X #%u\n", frame_type, _frames_of_type_seen);
                continue;
            }
        }

        psacp_receive_in_isr(&_contexts[i], frame);
    }

    return ARTIE_CAN_ERR_NONE;
}

static void _empty_rx_callback(const artie_can_frame_t *frame)
{
    // Only single-frame PUBs reach the callback; these tests collect whole messages instead.
    (void)frame;
}

/** Run one tick of the event loop for every node and advance the virtual clock by 1 ms. */
static void _run_event_loops(void)
{
    for (int i = 0; i < NUM_NODES; i++)
    {
        (void)psacp_tick(&_handles[i]);
    }
    _virtual_time_ms++;
}

void setUp(void)
{
    artie_can_error_t err;

    _virtual_time_ms = 0;
    _drop_frame_type = 0xFFU;
    _drop_nth = 0;
    _frames_of_type_seen = 0;
    _frames_dropped = 0;

    for (int i = 0; i < NUM_NODES; i++)
    {
        memset(&_contexts[i], 0, sizeof(_contexts[i]));
        memset(&_handles[i], 0, sizeof(_handles[i]));

        _handles[i].init = _bus_init;
        _handles[i].send = _bus_send;
        _handles[i].close = _bus_close;

        err = artie_can_init_custom(&_contexts[i], &_handles[i], _empty_rx_callback, _get_virtual_ms);
        TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

        err = artie_can_init_context_psacp(&_contexts[i], (uint8_t)(i + 1));
        TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);
    }

    err = artie_can_psacp_subscribe(&_contexts[SUBSCRIBER], TOPIC);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);
}

void tearDown(void)
{
    for (int i = 0; i < NUM_NODES; i++)
    {
        (void)artie_can_close(&_handles[i]);
    }
}

/**
 * @brief Publish a message from node 1 and drive every node's event loop until it is all sent.
 *
 * @param payload Buffer to publish.
 * @param nbytes Length of the payload.
 */
static void _publish_and_drain(const uint8_t *payload, uint16_t nbytes)
{
    artie_can_error_t err = artie_can_psacp_publish_message(&_handles[0], TOPIC, payload, nbytes,
                                                            ARTIE_CAN_FRAME_PRIORITY_PSACP_MEDIUM_LOW, false);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    while (artie_can_psacp_is_busy(&_handles[0]) && (_virtual_time_ms < MAX_VIRTUAL_MS))
    {
        _run_event_loops();
    }
    TEST_ASSERT_FALSE_MESSAGE(artie_can_psacp_is_busy(&_handles[0]), "Node 1 did not finish sending");
}

/** Fill a buffer with a varied pattern, so a misplaced fragment cannot pass by looking identical. */
static void _fill_pattern(uint8_t *buffer, uint16_t nbytes)
{
    for (uint16_t i = 0; i < nbytes; i++)
    {
        buffer[i] = (uint8_t)((i * 7U) & 0xFFU);
    }
}

/** Assert the subscriber has no message waiting, and that it counted one as dropped. */
static void _assert_dropped_not_delivered(void)
{
    artie_can_psacp_message_t message;
    artie_can_error_t err = artie_can_psacp_get_message(&_contexts[SUBSCRIBER], &message);

    TEST_ASSERT_EQUAL_INT_MESSAGE(ARTIE_CAN_ERR_NO_DATA, err,
                                  "A damaged message was delivered instead of being dropped");
    TEST_ASSERT_GREATER_THAN_UINT32_MESSAGE(0U, artie_can_psacp_dropped_count(&_contexts[SUBSCRIBER]),
                                            "The damaged message was not counted as dropped");
}

/** A message with nothing dropped arrives whole - the control for every test below. */
void test_intact_message_is_delivered(void)
{
    uint8_t payload[200];
    _fill_pattern(payload, sizeof(payload));

    _publish_and_drain(payload, sizeof(payload));

    artie_can_psacp_message_t message;
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, artie_can_psacp_get_message(&_contexts[SUBSCRIBER], &message));
    TEST_ASSERT_EQUAL_UINT16(sizeof(payload), message.nbytes);
    TEST_ASSERT_EQUAL_UINT8_ARRAY(payload, message.data, sizeof(payload));
    TEST_ASSERT_EQUAL_UINT8(1, message.source_address);
    TEST_ASSERT_EQUAL_UINT32(0U, artie_can_psacp_dropped_count(&_contexts[SUBSCRIBER]));
}

/** An interior PUB_MORE going missing leaves a gap in the fragment index. */
void test_lost_interior_fragment_drops_the_message(void)
{
    uint8_t payload[200];
    _fill_pattern(payload, sizeof(payload));

    _drop_frame_type = ARTIE_CAN_PSACP_FRAME_TYPE_PUB_MORE;
    _drop_nth = 5; // 200 bytes is 24 PUB_MOREs, so this is comfortably in the middle

    _publish_and_drain(payload, sizeof(payload));

    TEST_ASSERT_EQUAL_UINT32_MESSAGE(1U, _frames_dropped, "The drop was never injected");
    _assert_dropped_not_delivered();
}

/**
 * The last PUB_MORE going missing is the case that motivates PUB_START's count byte.
 *
 * PUB_END carries no index, so nothing about it alone distinguishes "the message ends here" from
 * "a fragment went missing and the message ends here". Only the promised count catches it.
 */
void test_lost_final_fragment_drops_the_message(void)
{
    uint8_t payload[200];
    _fill_pattern(payload, sizeof(payload));

    // 200 bytes = 7 in PUB_START + 24 PUB_MORE frames (192 bytes) + 1 byte in PUB_END.
    _drop_frame_type = ARTIE_CAN_PSACP_FRAME_TYPE_PUB_MORE;
    _drop_nth = 24;

    _publish_and_drain(payload, sizeof(payload));

    TEST_ASSERT_EQUAL_UINT32_MESSAGE(1U, _frames_dropped, "The drop was never injected");
    _assert_dropped_not_delivered();
}

/** Without a PUB_START there is no open slot, so every continuation is refused. */
void test_lost_start_drops_the_message(void)
{
    uint8_t payload[200];
    _fill_pattern(payload, sizeof(payload));

    _drop_frame_type = ARTIE_CAN_PSACP_FRAME_TYPE_PUB_START;
    _drop_nth = 1;

    _publish_and_drain(payload, sizeof(payload));

    TEST_ASSERT_EQUAL_UINT32_MESSAGE(1U, _frames_dropped, "The drop was never injected");
    _assert_dropped_not_delivered();
}

/** A message whose PUB_END never arrives is never completed, and its slot is reclaimed. */
void test_lost_end_drops_the_message(void)
{
    uint8_t payload[200];
    _fill_pattern(payload, sizeof(payload));

    _drop_frame_type = ARTIE_CAN_PSACP_FRAME_TYPE_PUB_END;
    _drop_nth = 1;

    _publish_and_drain(payload, sizeof(payload));

    TEST_ASSERT_EQUAL_UINT32_MESSAGE(1U, _frames_dropped, "The drop was never injected");

    // Nothing is delivered even before the timeout: the message is simply never complete.
    artie_can_psacp_message_t message;
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NO_DATA, artie_can_psacp_get_message(&_contexts[SUBSCRIBER], &message));

    // Ticking past the reassembly timeout reclaims the slot, which is what stops a publisher that
    // dies mid-message from wedging one of the subscriber's slots forever.
    uint64_t deadline = _virtual_time_ms + ARTIE_CAN_PSACP_REASSEMBLY_TIMEOUT_MS + 10U;
    while (_virtual_time_ms < deadline)
    {
        _run_event_loops();
    }

    _assert_dropped_not_delivered();
}

/**
 * A slot freed by the timeout is genuinely reusable: the next message through arrives intact.
 *
 * Without this, a publisher that lost one PUB_END would permanently cost the subscriber a slot.
 */
void test_slot_recovers_after_a_timeout(void)
{
    uint8_t payload[200];
    _fill_pattern(payload, sizeof(payload));

    _drop_frame_type = ARTIE_CAN_PSACP_FRAME_TYPE_PUB_END;
    _drop_nth = 1;
    _publish_and_drain(payload, sizeof(payload));

    uint64_t deadline = _virtual_time_ms + ARTIE_CAN_PSACP_REASSEMBLY_TIMEOUT_MS + 10U;
    while (_virtual_time_ms < deadline)
    {
        _run_event_loops();
    }

    // Now let everything through and publish again.
    _drop_frame_type = 0xFFU;
    _drop_nth = 0;
    _publish_and_drain(payload, sizeof(payload));

    artie_can_psacp_message_t message;
    TEST_ASSERT_EQUAL_INT_MESSAGE(ARTIE_CAN_ERR_NONE,
                                  artie_can_psacp_get_message(&_contexts[SUBSCRIBER], &message),
                                  "The slot was not reusable after its timeout");
    TEST_ASSERT_EQUAL_UINT16(sizeof(payload), message.nbytes);
    TEST_ASSERT_EQUAL_UINT8_ARRAY(payload, message.data, sizeof(payload));
}

/**
 * A new PUB_START reclaims a slot still holding an abandoned message from the same publisher.
 *
 * This is the fast path out of a lost PUB_END: a publisher that keeps publishing recovers on its
 * next message rather than waiting out the timeout.
 */
void test_new_message_reclaims_an_abandoned_slot(void)
{
    uint8_t payload[200];
    _fill_pattern(payload, sizeof(payload));

    _drop_frame_type = ARTIE_CAN_PSACP_FRAME_TYPE_PUB_END;
    _drop_nth = 1;
    _publish_and_drain(payload, sizeof(payload));

    // No waiting for the timeout - publish again straight away.
    _drop_frame_type = 0xFFU;
    _drop_nth = 0;
    _publish_and_drain(payload, sizeof(payload));

    artie_can_psacp_message_t message;
    TEST_ASSERT_EQUAL_INT_MESSAGE(ARTIE_CAN_ERR_NONE,
                                  artie_can_psacp_get_message(&_contexts[SUBSCRIBER], &message),
                                  "A new message did not reclaim the abandoned slot");
    TEST_ASSERT_EQUAL_UINT16(sizeof(payload), message.nbytes);
    TEST_ASSERT_EQUAL_UINT8_ARRAY(payload, message.data, sizeof(payload));

    // Exactly one message was lost - the first - and only one.
    TEST_ASSERT_EQUAL_UINT32(1U, artie_can_psacp_dropped_count(&_contexts[SUBSCRIBER]));
}

/** A single-frame PUB is unaffected by any of this: it has no fragments to lose. */
void test_single_frame_publish_is_unaffected(void)
{
    uint8_t payload[8];
    _fill_pattern(payload, sizeof(payload));

    // Drop every PUB_MORE there is; a single-frame message emits none.
    _drop_frame_type = ARTIE_CAN_PSACP_FRAME_TYPE_PUB_MORE;
    _drop_nth = 0;

    _publish_and_drain(payload, sizeof(payload));

    TEST_ASSERT_EQUAL_UINT32_MESSAGE(0U, _frames_dropped, "A single-frame publish emitted fragments");
    TEST_ASSERT_EQUAL_UINT32(0U, artie_can_psacp_dropped_count(&_contexts[SUBSCRIBER]));
}

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_intact_message_is_delivered);
    RUN_TEST(test_lost_interior_fragment_drops_the_message);
    RUN_TEST(test_lost_final_fragment_drops_the_message);
    RUN_TEST(test_lost_start_drops_the_message);
    RUN_TEST(test_lost_end_drops_the_message);
    RUN_TEST(test_slot_recovers_after_a_timeout);
    RUN_TEST(test_new_message_reclaims_an_abandoned_slot);
    RUN_TEST(test_single_frame_publish_is_unaffected);
    return UNITY_END();
}
