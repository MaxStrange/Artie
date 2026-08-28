/**
 * @file itest_node.c
 * @brief A single Artie CAN node in its own process, for the container-based integration tests.
 *
 * The unit tests put every node in one process, so frames never leave that process. This binary
 * exists to put each node in its own container instead, so that the UDP multicast backend, the
 * wire format, and the receiver thread all get exercised across a real network boundary.
 *
 * Two roles:
 *
 *  - `peer`   Long-lived. Enables all four protocols, then answers whatever it is sent: it echoes
 *             RTACP data frames back to their sender, acknowledges PSACP publishes and completed
 *             BWACP block writes with an RTACP marker, and services the ECHO RPC. Logs one line per
 *             event, which is what the artie-tool task greps for.
 *  - `driver` One-shot. Runs a single scenario against the peers, decides pass/fail itself, prints
 *             `ITEST <scenario>:PASS` (or `:FAIL <reason>`), and exits.
 *
 * Every node on the bus must have a unique address: the UDP multicast backend filters out its own
 * traffic by comparing the frame's source address against its own node address, so two nodes
 * sharing an address silently discard each other's frames.
 */

#include <signal.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "artie_can.h"
#include "backend_udp_mcast.h"

#ifdef _WIN32
    #include <windows.h>
    #ifdef _DEBUG
        #include <crtdbg.h>
    #endif
    #define SLEEP_MS(ms) Sleep(ms)
#else
    #include <time.h>
    #include <unistd.h>
    #define SLEEP_MS(ms) usleep((ms) * 1000)
#endif

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

/** Multicast group the integration-test bus lives on. Deliberately different from the groups the
 *  unit tests use, so a unit-test run on the same host can never be mistaken for bus traffic. */
#define DEFAULT_MCAST_GROUP "239.0.0.10"

/** Multicast port for the integration-test bus. */
#define DEFAULT_MCAST_PORT 7100U

/** PSACP topic the peers subscribe to (must be within the valid 0x0B-0xF4 range). */
#define ITEST_TOPIC 0x10U

/** Device-specific RPC procedure ID the peers register (0x00-0x0F are reserved by the library). */
#define ITEST_RPC_PROCEDURE_ID 0x10U

/** Argument the driver passes to the ECHO RPC; the peer returns this + 1. */
#define ITEST_RPC_ARG 0x41U

/** Size of each peer's BWACP receive buffer. */
#define ITEST_BWACP_BUFFER_SIZE 4096U

/** Size of the block the BWACP scenario transfers. Kept small so the whole suite stays fast. */
#define ITEST_BWACP_PAYLOAD_SIZE 1024U

/** How long the driver keeps retrying a scenario before giving up. */
#define DEFAULT_DRIVER_TIMEOUT_MS 15000U

/** How long the driver waits for peer responses within a single attempt. */
#define ATTEMPT_WAIT_MS 2000U

/** How long the driver listens, after a unicast has been answered, to prove nobody else answered. */
#define NEGATIVE_CHECK_MS 500U

/** How long a node ticks after init before doing anything, to let the multicast join settle. */
#define SETTLE_MS 250U

/** How long a send is retried while the protocol reports itself busy. */
#define SEND_RETRY_TIMEOUT_MS 500U

/** Maximum number of nodes; addresses are 6 bits. */
#define ADDRESS_COUNT 64U

// Markers exchanged on the wire. RTACP and PSACP carry at most 8 data bytes, so these must stay
// short. Each scenario uses its own marker so that a peer's log line from one test can never be
// mistaken for another's - the task streams peer logs from container start, and the peers outlive
// every individual test.
#define MARKER_PING "PING01"
#define MARKER_RTACP_UNICAST "RTUNI01"
#define MARKER_RTACP_BROADCAST "RTBC01"
#define MARKER_PSACP "PSPUB01"
#define MARKER_PSACP_ACK "PSOK01"
#define MARKER_PSACP_LARGE_ACK "PSL01"

/**
 * Size of the multi-frame PSACP message the large-message scenario publishes. Big enough to need a
 * long run of PUB_MORE frames (300 bytes is 38 frames) while keeping the suite quick. Kept in step
 * with PSACP_LARGE_PAYLOAD_SIZE in itest_node.py so either language's driver can be checked
 * against either language's peer.
 */
#define ITEST_PSACP_LARGE_SIZE 300U
#define MARKER_BWACP_ACK "BWOK01"

// ---------------------------------------------------------------------------
// Node state
// ---------------------------------------------------------------------------

static artie_can_context_t _context;
static artie_can_backend_t _node;
static artie_can_udp_mcast_context_t _udp_mcast_context;
static uint8_t _bwacp_receive_buffer[ITEST_BWACP_BUFFER_SIZE];

static uint8_t _node_address = 0x01U;
static volatile bool _should_stop = false;

/** A message handed from the backend's receiver thread to the main thread. */
typedef struct {
    uint8_t source;                             ///< Address of the node that sent it
    uint8_t topic;                              ///< PSACP topic (unused for RTACP)
    uint8_t nbytes;                             ///< Number of valid bytes in `data`
    uint8_t data[ARTIE_CAN_FRAME_MAX_DATA_LENGTH]; ///< Payload
} rx_msg_t;

/** Power-of-two length so the ring wraps with a mask. */
#define RX_QUEUE_LEN 32U
#define RX_QUEUE_MASK (RX_QUEUE_LEN - 1U)

/**
 * Single-producer/single-consumer rings. The rx callback runs on the backend's receiver thread, so
 * it may only append here; everything else (logging, sending, protocol calls) happens on the main
 * thread, which is the only thread allowed to drive the library.
 */
typedef struct {
    rx_msg_t entries[RX_QUEUE_LEN];
    volatile uint32_t head;   ///< Written by the receiver thread only
    volatile uint32_t tail;   ///< Written by the main thread only
} rx_queue_t;

static rx_queue_t _rtacp_queue;
static rx_queue_t _psacp_queue;

static void _queue_push(rx_queue_t *q, uint8_t source, uint8_t topic, uint8_t nbytes, const uint8_t *data)
{
    uint32_t head = q->head;
    uint32_t next = (head + 1U) & RX_QUEUE_MASK;
    if (next == q->tail)
    {
        return;  // Full; drop. A backlog this deep means the main loop has stalled anyway.
    }

    q->entries[head].source = source;
    q->entries[head].topic = topic;
    q->entries[head].nbytes = nbytes;
    for (uint8_t i = 0; i < nbytes && i < ARTIE_CAN_FRAME_MAX_DATA_LENGTH; i++)
    {
        q->entries[head].data[i] = data[i];
    }
    q->head = next;
}

static bool _queue_pop(rx_queue_t *q, rx_msg_t *out)
{
    uint32_t tail = q->tail;
    if (tail == q->head)
    {
        return false;
    }

    *out = q->entries[tail];
    q->tail = (tail + 1U) & RX_QUEUE_MASK;
    return true;
}

/** Renders a payload as a printable string so it can be logged and asserted on. */
static void _payload_to_string(const uint8_t *data, uint8_t nbytes, char *out, size_t out_size)
{
    size_t i = 0;
    for (; i < nbytes && (i + 1U) < out_size; i++)
    {
        out[i] = ((data[i] >= 0x20U) && (data[i] < 0x7FU)) ? (char)data[i] : '.';
    }
    out[i] = '\0';
}

/** True if the message's payload is exactly `marker`. */
static bool _payload_matches(const rx_msg_t *msg, const char *marker)
{
    size_t len = strlen(marker);
    if (msg->nbytes != (uint8_t)len)
    {
        return false;
    }
    return memcmp(msg->data, marker, len) == 0;
}

// ---------------------------------------------------------------------------
// Platform helpers
// ---------------------------------------------------------------------------

/** Monotonic milliseconds, for protocol timeouts. */
static uint64_t _get_current_time_ms(void)
{
#ifdef _WIN32
    return (uint64_t)GetTickCount64();
#else
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ((uint64_t)ts.tv_sec * 1000ULL) + ((uint64_t)ts.tv_nsec / 1000000ULL);
#endif
}

static void _handle_signal(int signum)
{
    (void)signum;
    _should_stop = true;
}

// ---------------------------------------------------------------------------
// Receive callback (runs on the backend's receiver thread)
// ---------------------------------------------------------------------------

static void _rx_callback(const artie_can_frame_t *frame)
{
    uint8_t protocol = (uint8_t)((frame->id & ARTIE_CAN_FRAME_ID_PROTOCOL_MASK) >> ARTIE_CAN_FRAME_ID_PROTOCOL_LOCATION);

    if (protocol == ARTIE_CAN_RTACP_PROTOCOL_ID)
    {
        artie_can_frame_rtacp_t rtacp_frame;
        if (artie_can_rtacp_parse_frame(frame, &rtacp_frame) != ARTIE_CAN_ERR_NONE)
        {
            return;
        }
        if (rtacp_frame.ack)
        {
            return;  // The library handles ACKs; only data frames are interesting here.
        }
        _queue_push(&_rtacp_queue, rtacp_frame.source_address, 0U, rtacp_frame.nbytes, rtacp_frame.data);
    }
    else if ((protocol == ARTIE_CAN_PSACP_HIGH_PROTOCOL_ID) || (protocol == ARTIE_CAN_PSACP_LOW_PROTOCOL_ID))
    {
        artie_can_frame_psacp_t psacp_frame;
        if (artie_can_psacp_parse_frame(frame, &psacp_frame) != ARTIE_CAN_ERR_NONE)
        {
            return;
        }
        _queue_push(&_psacp_queue, psacp_frame.source_address, psacp_frame.topic, psacp_frame.nbytes, psacp_frame.data);
    }
}

// ---------------------------------------------------------------------------
// Main-thread helpers
// ---------------------------------------------------------------------------

/** One tick of the event loop. Retriable errors are expected under load and are not failures. */
static bool _tick(void)
{
    artie_can_error_t err = artie_can_tick(&_node);
    if (err && !ARTIE_CAN_ERR_ONLY_RETRIABLE(err))
    {
        printf("NODE 0x%02X tick error: %d\n", _node_address, (int)err);
        fflush(stdout);
        return false;
    }
    return true;
}

/** Ticks the event loop for `duration_ms`. */
static void _pump(uint32_t duration_ms)
{
    uint64_t start = _get_current_time_ms();
    while ((_get_current_time_ms() - start) < (uint64_t)duration_ms)
    {
        (void)_tick();
        SLEEP_MS(1);
    }
}

/** Sends an RTACP data frame, retrying while the protocol reports itself busy. */
static artie_can_error_t _send_rtacp(uint8_t target, const char *payload)
{
    artie_can_frame_rtacp_t rtacp_frame;
    memset(&rtacp_frame, 0, sizeof(rtacp_frame));
    rtacp_frame.ack = false;
    rtacp_frame.priority = ARTIE_CAN_FRAME_PRIORITY_RTACP_MEDIUM;
    rtacp_frame.source_address = _node_address;
    rtacp_frame.target_address = target;
    rtacp_frame.nbytes = (uint8_t)strlen(payload);
    memcpy(rtacp_frame.data, payload, rtacp_frame.nbytes);

    artie_can_frame_t frame;
    artie_can_error_t err = artie_can_rtacp_init_frame(&frame, &rtacp_frame);
    if (err != ARTIE_CAN_ERR_NONE)
    {
        return err;
    }

    uint64_t start = _get_current_time_ms();
    do
    {
        err = artie_can_rtacp_send(&_node, &frame);
        if (err != ARTIE_CAN_ERR_SEND_BUSY)
        {
            return err;
        }
        (void)_tick();
        SLEEP_MS(1);
    } while ((_get_current_time_ms() - start) < (uint64_t)SEND_RETRY_TIMEOUT_MS);

    return err;
}

/** Publishes a PSACP message to `topic`. */
/**
 * @brief Build the payload the large-message scenario publishes.
 *
 * Varied rather than a repeated byte, so a fragment that arrives at the wrong offset or gets
 * duplicated shows up as a mismatch instead of passing by luck. itest_node.py builds the identical
 * pattern.
 *
 * @param out Buffer of at least ITEST_PSACP_LARGE_SIZE bytes.
 */
static void _fill_large_psacp_payload(uint8_t *out)
{
    for (uint16_t i = 0; i < ITEST_PSACP_LARGE_SIZE; i++)
    {
        out[i] = (uint8_t)(((i * 7U) + 3U) % 256U);
    }
}

static artie_can_error_t _publish_psacp(uint8_t topic, const char *payload)
{
    artie_can_frame_psacp_t psacp_frame;
    memset(&psacp_frame, 0, sizeof(psacp_frame));
    psacp_frame.high_priority = false;
    psacp_frame.priority = ARTIE_CAN_FRAME_PRIORITY_PSACP_MEDIUM_LOW;
    psacp_frame.source_address = _node_address;
    psacp_frame.topic = topic;
    psacp_frame.nbytes = (uint8_t)strlen(payload);
    memcpy(psacp_frame.data, payload, psacp_frame.nbytes);

    artie_can_frame_t frame;
    artie_can_error_t err = artie_can_psacp_init_frame(&frame, &psacp_frame);
    if (err != ARTIE_CAN_ERR_NONE)
    {
        return err;
    }

    return artie_can_psacp_publish(&_node, &frame);
}

// ---------------------------------------------------------------------------
// The ECHO RPC procedure (registered by peers, called by the driver)
// ---------------------------------------------------------------------------

/** Returns its uint8_t argument plus one. Runs inline on the peer's tick, i.e. the main thread. */
static void *_proc_echo(const void **params, uint8_t param_count, void *return_buffer, size_t return_buffer_size)
{
    (void)param_count;
    (void)return_buffer_size;

    uint8_t value;
    memcpy(&value, params[0], sizeof(value));
    uint8_t result = (uint8_t)(value + 1U);
    memcpy(return_buffer, &result, sizeof(result));

    printf("NODE 0x%02X RPC ECHO(0x%02X) -> 0x%02X\n", _node_address, value, result);
    fflush(stdout);

    return return_buffer;
}

// The signature is copied into the registry, but the strings and the return descriptor it points
// at are not, so they have to outlive the registration.
static char _rpc_type_name[] = "uint8_t";
static artie_can_rpc_param_descriptor_t _rpc_return_descriptor;

static void _init_echo_signature(artie_can_rpc_signature_t *sig)
{
    _rpc_return_descriptor.type_name = _rpc_type_name;
    _rpc_return_descriptor.offset_in_msgpack = 0;
    _rpc_return_descriptor.optional = false;

    memset(sig, 0, sizeof(*sig));
    sig->procedure_id = ITEST_RPC_PROCEDURE_ID;
    sig->name = "ECHO";
    sig->synchronous = true;
    sig->param_count = 1;
    sig->params[0].type_name = _rpc_type_name;
    sig->params[0].offset_in_msgpack = 0;
    sig->params[0].optional = false;
    sig->function = _proc_echo;
    sig->return_descriptor = &_rpc_return_descriptor;
    sig->return_size = sizeof(uint8_t);
}

// ---------------------------------------------------------------------------
// Node bring-up
// ---------------------------------------------------------------------------

/**
 * Brings this node up on the bus. Order matters: the backend context first, then every protocol
 * context (all with the same node address, since they share `context.node_address`), and only then
 * artie_can_init(), which refuses to run with no protocol flags set.
 */
static bool _node_init(const char *group, uint16_t port, uint8_t node_class)
{
    artie_can_error_t err = artie_can_init_context_udp_mcast(&_context, &_udp_mcast_context, group, port);
    if (err != ARTIE_CAN_ERR_NONE)
    {
        printf("NODE 0x%02X failed to init multicast context: %d\n", _node_address, (int)err);
        return false;
    }

    err = artie_can_init_context_rtacp(&_context, _node_address);
    if (err != ARTIE_CAN_ERR_NONE)
    {
        printf("NODE 0x%02X failed to init RTACP context: %d\n", _node_address, (int)err);
        return false;
    }

    err = artie_can_init_context_psacp(&_context, _node_address);
    if (err != ARTIE_CAN_ERR_NONE)
    {
        printf("NODE 0x%02X failed to init PSACP context: %d\n", _node_address, (int)err);
        return false;
    }

    err = artie_can_init_context_bwacp(&_context, _node_address, node_class);
    if (err != ARTIE_CAN_ERR_NONE)
    {
        printf("NODE 0x%02X failed to init BWACP context: %d\n", _node_address, (int)err);
        return false;
    }

    err = artie_can_init_context_rpcacp(&_context, _node_address, node_class, "itest-node", "1.0.0");
    if (err != ARTIE_CAN_ERR_NONE)
    {
        printf("NODE 0x%02X failed to init RPCACP context: %d\n", _node_address, (int)err);
        return false;
    }

    err = artie_can_bwacp_set_receive_buffer(&_context, _bwacp_receive_buffer, sizeof(_bwacp_receive_buffer));
    if (err != ARTIE_CAN_ERR_NONE)
    {
        printf("NODE 0x%02X failed to set BWACP receive buffer: %d\n", _node_address, (int)err);
        return false;
    }

    err = artie_can_init(&_context, &_node, ARTIE_CAN_BACKEND_UDP_MCAST, _rx_callback, _get_current_time_ms);
    if (err != ARTIE_CAN_ERR_NONE)
    {
        printf("NODE 0x%02X failed to init backend: %d\n", _node_address, (int)err);
        return false;
    }

    return true;
}

// ---------------------------------------------------------------------------
// Peer role
// ---------------------------------------------------------------------------

static int _run_peer(void)
{
    artie_can_rpc_signature_t sig;
    _init_echo_signature(&sig);
    artie_can_error_t err = artie_can_rpcacp_register_procedure(&_node, &sig);
    if (err != ARTIE_CAN_ERR_NONE)
    {
        printf("NODE 0x%02X failed to register ECHO procedure: %d\n", _node_address, (int)err);
        return 1;
    }

    err = artie_can_psacp_subscribe(&_context, ITEST_TOPIC);
    if (err != ARTIE_CAN_ERR_NONE)
    {
        printf("NODE 0x%02X failed to subscribe to topic 0x%02X: %d\n", _node_address, ITEST_TOPIC, (int)err);
        return 1;
    }

    printf("NODE 0x%02X ready\n", _node_address);
    fflush(stdout);

    uint64_t last_bwacp_completion = _context.bwacp_context.last_completed_timestamp_ms;

    while (!_should_stop)
    {
        (void)_tick();

        rx_msg_t msg;
        char payload[ARTIE_CAN_FRAME_MAX_DATA_LENGTH + 1U];

        // RTACP: log it and echo the same payload back, so the sender can prove it made the round trip.
        while (_queue_pop(&_rtacp_queue, &msg))
        {
            _payload_to_string(msg.data, msg.nbytes, payload, sizeof(payload));
            printf("NODE 0x%02X RTACP RX from 0x%02X: %s\n", _node_address, msg.source, payload);
            fflush(stdout);

            err = _send_rtacp(msg.source, payload);
            if (err != ARTIE_CAN_ERR_NONE)
            {
                printf("NODE 0x%02X failed to echo to 0x%02X: %d\n", _node_address, msg.source, (int)err);
                fflush(stdout);
            }
        }

        // PSACP: log it and acknowledge over RTACP.
        while (_queue_pop(&_psacp_queue, &msg))
        {
            _payload_to_string(msg.data, msg.nbytes, payload, sizeof(payload));
            printf("NODE 0x%02X PSACP RX topic 0x%02X from 0x%02X: %s\n", _node_address, msg.topic, msg.source, payload);
            fflush(stdout);

            err = _send_rtacp(msg.source, MARKER_PSACP_ACK);
            if (err != ARTIE_CAN_ERR_NONE)
            {
                printf("NODE 0x%02X failed to ack PSACP to 0x%02X: %d\n", _node_address, msg.source, (int)err);
                fflush(stdout);
            }
        }

        // Multi-frame PSACP messages do not reach the rx callback - they are not a frame - so they
        // are collected from the library once it has reassembled them.
        artie_can_psacp_message_t large_message;
        while (artie_can_psacp_get_message(&_context, &large_message) == ARTIE_CAN_ERR_NONE)
        {
            static uint8_t expected[ITEST_PSACP_LARGE_SIZE];
            _fill_large_psacp_payload(expected);

            bool intact = (large_message.nbytes == ITEST_PSACP_LARGE_SIZE) &&
                          (memcmp(large_message.data, expected, ITEST_PSACP_LARGE_SIZE) == 0);

            // The length alone would pass even with fragments at the wrong offsets, so the peer
            // only acknowledges after checking the payload byte for byte.
            printf("NODE 0x%02X PSACP RX topic 0x%02X from 0x%02X: %u bytes, %s\n",
                   _node_address, large_message.topic, large_message.source_address,
                   (unsigned int)large_message.nbytes, intact ? "intact" : "CORRUPT");
            fflush(stdout);

            if (intact)
            {
                err = _send_rtacp(large_message.source_address, MARKER_PSACP_LARGE_ACK);
                if (err != ARTIE_CAN_ERR_NONE)
                {
                    printf("NODE 0x%02X failed to ack large PSACP to 0x%02X: %d\n",
                           _node_address, large_message.source_address, (int)err);
                    fflush(stdout);
                }
            }
        }

        // BWACP has no completion callback, so watch the context for a newly finished transfer.
        if (_context.bwacp_context.last_completed_timestamp_ms != last_bwacp_completion)
        {
            last_bwacp_completion = _context.bwacp_context.last_completed_timestamp_ms;
            uint8_t sender = _context.bwacp_context.last_completed_sender_address;
            printf("NODE 0x%02X BWACP RX %u bytes from 0x%02X at offset %u\n",
                   _node_address,
                   (unsigned int)_context.bwacp_context.receive_bytes_written,
                   sender,
                   (unsigned int)_context.bwacp_context.last_completed_receive_address);
            fflush(stdout);

            err = _send_rtacp(sender, MARKER_BWACP_ACK);
            if (err != ARTIE_CAN_ERR_NONE)
            {
                printf("NODE 0x%02X failed to ack BWACP to 0x%02X: %d\n", _node_address, sender, (int)err);
                fflush(stdout);
            }
        }

        SLEEP_MS(1);
    }

    printf("NODE 0x%02X shutting down\n", _node_address);
    fflush(stdout);
    artie_can_close(&_node);
    return 0;
}

// ---------------------------------------------------------------------------
// Driver role
// ---------------------------------------------------------------------------

/**
 * Ticks for up to `timeout_ms`, recording which nodes answered with `marker`. Returns as soon as
 * every address in `expect` has answered.
 */
static void _collect_responses(const char *marker, uint32_t timeout_ms, bool seen[ADDRESS_COUNT],
                               const uint8_t *expect, uint8_t expect_count)
{
    uint64_t start = _get_current_time_ms();

    while ((_get_current_time_ms() - start) < (uint64_t)timeout_ms)
    {
        (void)_tick();

        rx_msg_t msg;
        while (_queue_pop(&_rtacp_queue, &msg))
        {
            if (_payload_matches(&msg, marker) && (msg.source < ADDRESS_COUNT))
            {
                seen[msg.source] = true;
            }
        }

        bool all_seen = true;
        for (uint8_t i = 0; i < expect_count; i++)
        {
            if (!seen[expect[i]])
            {
                all_seen = false;
                break;
            }
        }
        if (all_seen)
        {
            return;
        }

        SLEEP_MS(1);
    }
}

/** Sends `marker` to `target` and waits for every address in `expect` to echo it back. */
static bool _attempt_rtacp(uint8_t target, const char *marker, const uint8_t *expect, uint8_t expect_count,
                           bool seen[ADDRESS_COUNT], char *reason, size_t reason_size)
{
    artie_can_error_t err = _send_rtacp(target, marker);
    if (err != ARTIE_CAN_ERR_NONE)
    {
        snprintf(reason, reason_size, "send returned %d", (int)err);
        return false;
    }

    _collect_responses(marker, ATTEMPT_WAIT_MS, seen, expect, expect_count);

    for (uint8_t i = 0; i < expect_count; i++)
    {
        if (!seen[expect[i]])
        {
            snprintf(reason, reason_size, "no echo from 0x%02X", expect[i]);
            return false;
        }
    }
    return true;
}

static bool _scenario_ping(char *reason, size_t reason_size)
{
    static const uint8_t expect[] = {0x02U, 0x03U};
    bool seen[ADDRESS_COUNT] = {false};
    return _attempt_rtacp(ARTIE_CAN_RTACP_TARGET_ADDRESS_BROADCAST, MARKER_PING, expect,
                          (uint8_t)(sizeof(expect) / sizeof(expect[0])), seen, reason, reason_size);
}

static bool _scenario_rtacp_broadcast(char *reason, size_t reason_size)
{
    static const uint8_t expect[] = {0x02U, 0x03U};
    bool seen[ADDRESS_COUNT] = {false};
    return _attempt_rtacp(ARTIE_CAN_RTACP_TARGET_ADDRESS_BROADCAST, MARKER_RTACP_BROADCAST, expect,
                          (uint8_t)(sizeof(expect) / sizeof(expect[0])), seen, reason, reason_size);
}

/**
 * A unicast has to be answered by its target and ignored by everyone else. The negative half is
 * checked here rather than in the task YAML because artietool's container-scoped
 * `unexpected-outputs` never get bound to a container.
 */
static bool _scenario_rtacp_unicast(char *reason, size_t reason_size)
{
    static const uint8_t expect[] = {0x02U};
    bool seen[ADDRESS_COUNT] = {false};

    if (!_attempt_rtacp(0x02U, MARKER_RTACP_UNICAST, expect,
                        (uint8_t)(sizeof(expect) / sizeof(expect[0])), seen, reason, reason_size))
    {
        return false;
    }

    // Keep listening: nothing but the target should have answered.
    _collect_responses(MARKER_RTACP_UNICAST, NEGATIVE_CHECK_MS, seen, NULL, 0);
    if (seen[0x03U])
    {
        snprintf(reason, reason_size, "non-target node 0x03 answered a unicast addressed to 0x02");
        return false;
    }
    return true;
}

static bool _scenario_psacp(char *reason, size_t reason_size)
{
    static const uint8_t expect[] = {0x02U, 0x03U};
    bool seen[ADDRESS_COUNT] = {false};

    artie_can_error_t err = _publish_psacp(ITEST_TOPIC, MARKER_PSACP);
    if (err != ARTIE_CAN_ERR_NONE)
    {
        snprintf(reason, reason_size, "publish returned %d", (int)err);
        return false;
    }

    _collect_responses(MARKER_PSACP_ACK, ATTEMPT_WAIT_MS, seen, expect,
                       (uint8_t)(sizeof(expect) / sizeof(expect[0])));

    for (uint8_t i = 0; i < (uint8_t)(sizeof(expect) / sizeof(expect[0])); i++)
    {
        if (!seen[expect[i]])
        {
            snprintf(reason, reason_size, "subscriber 0x%02X did not acknowledge the publish", expect[i]);
            return false;
        }
    }
    return true;
}

/**
 * @brief Publish a message far larger than one CAN frame and check both peers reassemble it whole.
 *
 * The peers only answer once they have compared the payload byte for byte, so an acknowledgement
 * means the message survived the trip across the container boundary intact, not merely that
 * something of the right length turned up.
 */
static bool _scenario_psacp_large(char *reason, size_t reason_size)
{
    static const uint8_t expect[] = {0x02U, 0x03U};
    bool seen[ADDRESS_COUNT] = {false};
    static uint8_t payload[ITEST_PSACP_LARGE_SIZE];

    _fill_large_psacp_payload(payload);

    artie_can_error_t err = artie_can_psacp_publish_message(&_node, ITEST_TOPIC, payload, ITEST_PSACP_LARGE_SIZE,
                                                            ARTIE_CAN_FRAME_PRIORITY_PSACP_MEDIUM_LOW, false);
    if (err != ARTIE_CAN_ERR_NONE)
    {
        snprintf(reason, reason_size, "publish returned %d", (int)err);
        return false;
    }

    // The message is emitted across ticks rather than inside the call, so let it drain first.
    for (uint32_t elapsed = 0; artie_can_psacp_is_busy(&_node) && (elapsed < ATTEMPT_WAIT_MS); elapsed++)
    {
        (void)artie_can_tick(&_node);
        SLEEP_MS(1);
    }

    if (artie_can_psacp_is_busy(&_node))
    {
        snprintf(reason, reason_size, "the publish never finished sending");
        return false;
    }

    _collect_responses(MARKER_PSACP_LARGE_ACK, ATTEMPT_WAIT_MS, seen, expect,
                       (uint8_t)(sizeof(expect) / sizeof(expect[0])));

    for (uint8_t i = 0; i < (uint8_t)(sizeof(expect) / sizeof(expect[0])); i++)
    {
        if (!seen[expect[i]])
        {
            snprintf(reason, reason_size, "subscriber 0x%02X did not report an intact message", expect[i]);
            return false;
        }
    }
    return true;
}

static bool _scenario_bwacp(char *reason, size_t reason_size)
{
    static const uint8_t expect[] = {0x02U};
    bool seen[ADDRESS_COUNT] = {false};
    static uint8_t payload[ITEST_BWACP_PAYLOAD_SIZE];

    for (uint32_t i = 0; i < ITEST_BWACP_PAYLOAD_SIZE; i++)
    {
        payload[i] = (uint8_t)((i * 7U) + 3U);
    }

    artie_can_error_t err = artie_can_bwacp_send(&_node, payload, ITEST_BWACP_PAYLOAD_SIZE, 0U, 0x02U, 0U,
                                                 ARTIE_CAN_FRAME_PRIORITY_BWACP_MEDIUM);
    if (err != ARTIE_CAN_ERR_NONE)
    {
        snprintf(reason, reason_size, "block write returned %d", (int)err);
        return false;
    }

    // Drive the transfer to completion.
    uint64_t start = _get_current_time_ms();
    while (artie_can_bwacp_is_busy(&_node))
    {
        if ((_get_current_time_ms() - start) >= (uint64_t)ATTEMPT_WAIT_MS)
        {
            snprintf(reason, reason_size, "block write did not complete within %u ms", (unsigned int)ATTEMPT_WAIT_MS);
            return false;
        }
        (void)_tick();
        SLEEP_MS(1);
    }

    _collect_responses(MARKER_BWACP_ACK, ATTEMPT_WAIT_MS, seen, expect,
                       (uint8_t)(sizeof(expect) / sizeof(expect[0])));
    if (!seen[0x02U])
    {
        snprintf(reason, reason_size, "receiver 0x02 did not acknowledge the block");
        return false;
    }
    return true;
}

static bool _scenario_rpcacp(char *reason, size_t reason_size)
{
    artie_can_rpc_signature_t sig;
    _init_echo_signature(&sig);

    uint8_t arg = ITEST_RPC_ARG;
    artie_can_rpc_value_t args[1];
    args[0].data = &arg;
    args[0].size = sizeof(arg);

    artie_can_error_t err = artie_can_rpcacp_call(&_node, 0x02U, &sig, args, 1U);
    if (err != ARTIE_CAN_ERR_NONE)
    {
        snprintf(reason, reason_size, "call returned %d", (int)err);
        return false;
    }

    uint64_t start = _get_current_time_ms();
    while (artie_can_rpcacp_is_busy(&_node))
    {
        if ((_get_current_time_ms() - start) >= (uint64_t)ATTEMPT_WAIT_MS)
        {
            snprintf(reason, reason_size, "call did not complete within %u ms", (unsigned int)ATTEMPT_WAIT_MS);
            return false;
        }
        (void)_tick();
        SLEEP_MS(1);
    }

    uint8_t errno_code = 0;
    err = artie_can_rpcacp_get_last_error(&_node, &errno_code);
    if (err != ARTIE_CAN_ERR_NONE)
    {
        snprintf(reason, reason_size, "call failed with %d (errno 0x%02X)", (int)err, errno_code);
        return false;
    }

    uint8_t result = 0;
    err = artie_can_rpcacp_get_result(&_node, &sig, &result, sizeof(result));
    if (err != ARTIE_CAN_ERR_NONE)
    {
        snprintf(reason, reason_size, "could not read the result: %d", (int)err);
        return false;
    }

    if (result != (uint8_t)(ITEST_RPC_ARG + 1U))
    {
        snprintf(reason, reason_size, "expected 0x%02X, got 0x%02X", (uint8_t)(ITEST_RPC_ARG + 1U), result);
        return false;
    }
    return true;
}

typedef bool (*scenario_fn_t)(char *reason, size_t reason_size);

typedef struct {
    const char *name;
    scenario_fn_t fn;
} scenario_t;

static const scenario_t _scenarios[] = {
    {"ping", _scenario_ping},
    {"rtacp-unicast", _scenario_rtacp_unicast},
    {"rtacp-broadcast", _scenario_rtacp_broadcast},
    {"bwacp-block-transfer", _scenario_bwacp},
    {"psacp-publish-subscribe", _scenario_psacp},
    {"psacp-large-message", _scenario_psacp_large},
    {"rpcacp-call", _scenario_rpcacp},
};

static int _run_driver(const char *scenario_name, uint32_t timeout_ms)
{
    const scenario_t *scenario = NULL;
    for (size_t i = 0; i < (sizeof(_scenarios) / sizeof(_scenarios[0])); i++)
    {
        if (strcmp(_scenarios[i].name, scenario_name) == 0)
        {
            scenario = &_scenarios[i];
            break;
        }
    }

    if (scenario == NULL)
    {
        printf("ITEST %s:FAIL unknown scenario\n", scenario_name);
        fflush(stdout);
        return 2;
    }

    // Let the multicast join settle before saying anything on the bus.
    _pump(SETTLE_MS);

    // Retry the whole attempt until the timeout: compose reports the peers as up as soon as their
    // containers start, which can be before they have actually joined the group.
    char reason[128] = {0};
    uint64_t start = _get_current_time_ms();
    do
    {
        if (scenario->fn(reason, sizeof(reason)))
        {
            printf("ITEST %s:PASS\n", scenario->name);
            fflush(stdout);
            artie_can_close(&_node);
            return 0;
        }
    } while ((_get_current_time_ms() - start) < (uint64_t)timeout_ms);

    printf("ITEST %s:FAIL %s\n", scenario->name, reason);
    fflush(stdout);
    artie_can_close(&_node);
    return 1;
}

// ---------------------------------------------------------------------------
// Entry point
// ---------------------------------------------------------------------------

static void _usage(const char *program)
{
    printf("Usage:\n");
    printf("  %s --role peer   --address <addr> [--group <ip>] [--port <port>]\n", program);
    printf("  %s --role driver --address <addr> --scenario <name> [--group <ip>] [--port <port>] [--timeout-ms <ms>]\n", program);
    printf("\nScenarios:\n");
    for (size_t i = 0; i < (sizeof(_scenarios) / sizeof(_scenarios[0])); i++)
    {
        printf("  %s\n", _scenarios[i].name);
    }
}

int main(int argc, char **argv)
{
    const char *role = NULL;
    const char *scenario = NULL;
    const char *group = DEFAULT_MCAST_GROUP;
    uint16_t port = (uint16_t)DEFAULT_MCAST_PORT;
    uint32_t timeout_ms = DEFAULT_DRIVER_TIMEOUT_MS;

#if defined(_WIN32) && defined(_DEBUG)
    // A debug-CRT assertion opens a modal dialog by default, which is useless in the container this
    // node is built to run in - the process just hangs with nobody to click OK - and worse than
    // useless when running it by hand on a Windows box, where the dialog steals focus and the
    // message is gone before it can be read. Send the report to stderr instead, where it lands in
    // the container logs the test task already collects.
    for (int report_type = 0; report_type < _CRT_ERRCNT; report_type++)
    {
        _CrtSetReportMode(report_type, _CRTDBG_MODE_FILE);
        _CrtSetReportFile(report_type, _CRTDBG_FILE_STDERR);
    }
#endif

    for (int i = 1; i < argc; i++)
    {
        bool has_value = (i + 1) < argc;
        if ((strcmp(argv[i], "--role") == 0) && has_value)
        {
            role = argv[++i];
        }
        else if ((strcmp(argv[i], "--address") == 0) && has_value)
        {
            _node_address = (uint8_t)strtoul(argv[++i], NULL, 0);
        }
        else if ((strcmp(argv[i], "--scenario") == 0) && has_value)
        {
            scenario = argv[++i];
        }
        else if ((strcmp(argv[i], "--group") == 0) && has_value)
        {
            group = argv[++i];
        }
        else if ((strcmp(argv[i], "--port") == 0) && has_value)
        {
            port = (uint16_t)strtoul(argv[++i], NULL, 0);
        }
        else if ((strcmp(argv[i], "--timeout-ms") == 0) && has_value)
        {
            timeout_ms = (uint32_t)strtoul(argv[++i], NULL, 0);
        }
        else
        {
            printf("Unrecognized or incomplete argument: %s\n", argv[i]);
            _usage(argv[0]);
            return 2;
        }
    }

    if (role == NULL)
    {
        _usage(argv[0]);
        return 2;
    }

    signal(SIGINT, _handle_signal);
    signal(SIGTERM, _handle_signal);

    // Line buffering keeps the log readable when stdout is a pipe, which is how the test task
    // reads it. The size has to be a real one even though the buffer is left to the CRT to
    // allocate: glibc quietly picks a default when passed 0, but the Windows UCRT asserts that it
    // is at least 2, which killed this process before its first line of output.
    setvbuf(stdout, NULL, _IOLBF, BUFSIZ);

    printf("NODE 0x%02X starting: role=%s group=%s port=%u\n", _node_address, role, group, (unsigned int)port);
    fflush(stdout);

    uint8_t node_class = (strcmp(role, "peer") == 0) ? (uint8_t)ARTIE_CAN_BWACP_CLASS_SENSOR
                                                     : (uint8_t)ARTIE_CAN_BWACP_CLASS_SBC;
    if (!_node_init(group, port, node_class))
    {
        return 1;
    }

    if (strcmp(role, "peer") == 0)
    {
        return _run_peer();
    }
    else if (strcmp(role, "driver") == 0)
    {
        if (scenario == NULL)
        {
            printf("--scenario is required for the driver role\n");
            _usage(argv[0]);
            artie_can_close(&_node);
            return 2;
        }
        return _run_driver(scenario, timeout_ms);
    }

    printf("Unknown role: %s\n", role);
    _usage(argv[0]);
    artie_can_close(&_node);
    return 2;
}
