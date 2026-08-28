/**
 * @file psacp.c
 * @brief Implementation of PSACP (Pub/Sub Artie CAN Protocol).
 *
 */

#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#include "backend.h"
#include "context.h"
#include "err.h"
#include "frame.h"
#include "log.h"
#include "psacp.h"
#include "psacp_context.h"
#include "util.h"

/* The reassembly slots are sized by a literal in psacp_context.h, which cannot refer to
 * ARTIE_CAN_PSACP_MAX_MESSAGE_SIZE because psacp.h includes context.h, which includes that header.
 * Pin the two together here so they cannot drift apart silently. */
#if (ARTIE_CAN_PSACP_SLOT_BUFFER_SIZE != ARTIE_CAN_PSACP_MAX_MESSAGE_SIZE)
#error "ARTIE_CAN_PSACP_SLOT_BUFFER_SIZE must equal ARTIE_CAN_PSACP_MAX_MESSAGE_SIZE"
#endif

/**
 * @brief Work out how a payload splits across frames.
 *
 * PUB_START carries ARTIE_CAN_PSACP_START_PAYLOAD_BYTES, each PUB_MORE carries a full frame, and
 * PUB_END carries whatever is left - between 1 and 8 bytes, never 0, so the last frame of a
 * message always carries data.
 *
 * @param nbytes Length of the payload; must be greater than ARTIE_CAN_PSACP_MAX_DATA_BYTES.
 * @param more_count_out Receives the number of PUB_MORE frames needed.
 * @param end_bytes_out Receives the number of bytes the PUB_END frame carries.
 */
static void _plan_fragmentation(uint16_t nbytes, uint8_t *more_count_out, uint8_t *end_bytes_out)
{
    uint16_t remaining = (uint16_t)(nbytes - ARTIE_CAN_PSACP_START_PAYLOAD_BYTES);
    uint16_t more_count = (uint16_t)((remaining - 1U) / ARTIE_CAN_PSACP_MAX_DATA_BYTES);

    *more_count_out = (uint8_t)more_count;
    *end_bytes_out = (uint8_t)(remaining - (more_count * ARTIE_CAN_PSACP_MAX_DATA_BYTES));
}

/** Extract the frame type from a frame's ID. */
static uint8_t _frame_type(const artie_can_frame_t *frame)
{
    return (uint8_t)((frame->id & (uint32_t)ARTIE_CAN_FRAME_ID_FRAME_TYPE_MASK) >> (uint32_t)ARTIE_CAN_FRAME_ID_FRAME_TYPE_LOCATION);
}

/** Extract the topic from a frame's ID. */
static uint8_t _frame_topic(const artie_can_frame_t *frame)
{
    return (uint8_t)((frame->id & (uint32_t)PSACP_FRAME_ID_TOPIC_MASK) >> (uint32_t)PSACP_FRAME_ID_TOPIC_LOCATION);
}

/** Extract the sender address from a frame's ID. */
static uint8_t _frame_source(const artie_can_frame_t *frame)
{
    return (uint8_t)((frame->id & (uint32_t)ARTIE_CAN_FRAME_ID_SENDER_ADDRESS_MASK) >> (uint32_t)ARTIE_CAN_FRAME_ID_SENDER_ADDRESS_LOCATION);
}

/** Extract the fragment index from a PUB_MORE frame's ID. */
static uint8_t _frame_index(const artie_can_frame_t *frame)
{
    return (uint8_t)((frame->id & (uint32_t)PSACP_FRAME_ID_INDEX_MASK) >> (uint32_t)PSACP_FRAME_ID_INDEX_LOCATION);
}

/**
 * @brief Build one frame of a PSACP message.
 *
 * @param out The frame to populate.
 * @param frame_type One of the ARTIE_CAN_PSACP_FRAME_TYPE_* values.
 * @param high_priority Whether to use the high-priority PSACP protocol ID.
 * @param priority User-assigned priority within the protocol.
 * @param source_address This node's address.
 * @param topic The topic being published to.
 * @param index Fragment index; only meaningful for PUB_MORE, pass 0 otherwise.
 * @param data Payload bytes for this frame.
 * @param nbytes Number of payload bytes, at most ARTIE_CAN_PSACP_MAX_DATA_BYTES.
 */
static void _build_frame(artie_can_frame_t *out, uint8_t frame_type, bool high_priority, uint8_t priority,
                         uint8_t source_address, uint8_t topic, uint8_t index, const uint8_t *data, uint8_t nbytes)
{
    uint8_t protocol_id = high_priority ? ARTIE_CAN_PSACP_HIGH_PROTOCOL_ID : ARTIE_CAN_PSACP_LOW_PROTOCOL_ID;

    out->id = ((uint32_t)protocol_id << (uint32_t)ARTIE_CAN_FRAME_ID_PROTOCOL_LOCATION) |
              ((uint32_t)frame_type << (uint32_t)ARTIE_CAN_FRAME_ID_FRAME_TYPE_LOCATION) |
              ((uint32_t)priority << (uint32_t)ARTIE_CAN_FRAME_ID_USER_PRIORITY_LOCATION) |
              ((uint32_t)source_address << (uint32_t)ARTIE_CAN_FRAME_ID_SENDER_ADDRESS_LOCATION) |
              ((uint32_t)topic << (uint32_t)PSACP_FRAME_ID_TOPIC_LOCATION) |
              (((uint32_t)index << (uint32_t)PSACP_FRAME_ID_INDEX_LOCATION) & (uint32_t)PSACP_FRAME_ID_INDEX_MASK);

    out->dlc = nbytes;
    memset(out->data, 0, sizeof(out->data));
    if (nbytes > 0U)
    {
        memcpy(out->data, data, nbytes);
    }
}

/**
 * @brief Check whether this node is subscribed to the given topic.
 * Broadcast (topic 0x00) always returns true.
 */
static bool _is_subscribed(const psacp_context_t *ctx, uint8_t topic)
{
    if (topic == ARTIE_CAN_PSACP_TOPIC_BROADCAST)
    {
        return true;
    }

    for (uint8_t i = 0; i < ctx->subscribed_topic_count; i++)
    {
        if (ctx->subscribed_topics[i] == topic)
        {
            return true;
        }
    }

    return false;
}

artie_can_error_t artie_can_init_context_psacp(artie_can_context_t *ctx, uint8_t node_address)
{
    if (ctx == NULL)
    {
        return ARTIE_CAN_ERR_INVALID_ARG;
    }
    else if (node_address == 0U)
    {
        // Address 0 is reserved for broadcast; nodes must have a non-zero address
        return ARTIE_CAN_ERR_INVALID_ARG;
    }
    else if (node_address > (ARTIE_CAN_FRAME_ID_SENDER_ADDRESS_MASK >> ARTIE_CAN_FRAME_ID_SENDER_ADDRESS_LOCATION))
    {
        return ARTIE_CAN_ERR_INVALID_ARG;
    }

    ctx->psacp_context.node_address = node_address;
    ctx->psacp_context.subscribed_topic_count = 0;
    memset(ctx->psacp_context.subscribed_topics, 0, sizeof(ctx->psacp_context.subscribed_topics));

    // Reassembly and send state start empty. The slots' payload buffers are deliberately not
    // cleared: they are large, and nothing reads a byte of one that has not been written first.
    for (uint8_t i = 0; i < ARTIE_CAN_PSACP_REASSEMBLY_SLOTS; i++)
    {
        ctx->psacp_context.slots[i].state = PSACP_SLOT_FREE;
        ctx->psacp_context.slots[i].nbytes = 0;
    }
    ctx->psacp_context.send.active = false;
    ctx->psacp_context.dropped_message_count = 0;

    ctx->protocol_flags |= ARTIE_CAN_PROTOCOL_FLAG_PSACP;
    ctx->node_address = node_address;

    return ARTIE_CAN_ERR_NONE;
}

artie_can_error_t artie_can_psacp_subscribe(artie_can_context_t *ctx, uint8_t topic)
{
    if (ctx == NULL)
    {
        return ARTIE_CAN_ERR_INVALID_ARG;
    }

    // Broadcast is implicit - no need to subscribe explicitly
    if (topic == ARTIE_CAN_PSACP_TOPIC_BROADCAST)
    {
        return ARTIE_CAN_ERR_INVALID_ARG;
    }

    // Check if already subscribed
    for (uint8_t i = 0; i < ctx->psacp_context.subscribed_topic_count; i++)
    {
        if (ctx->psacp_context.subscribed_topics[i] == topic)
        {
            // Already subscribed, nothing to do
            return ARTIE_CAN_ERR_NONE;
        }
    }

    // Check capacity
    if (ctx->psacp_context.subscribed_topic_count >= ARTIE_CAN_PSACP_MAX_SUBSCRIPTIONS)
    {
        return ARTIE_CAN_ERR_NO_SPACE;
    }

    ctx->psacp_context.subscribed_topics[ctx->psacp_context.subscribed_topic_count] = topic;
    ctx->psacp_context.subscribed_topic_count++;

    ARTIE_CAN_LOG(ctx, "PSACP: Subscribed to topic 0x%02X (total subscriptions: %u)\n", topic, ctx->psacp_context.subscribed_topic_count);

    return ARTIE_CAN_ERR_NONE;
}

artie_can_error_t artie_can_psacp_unsubscribe(artie_can_context_t *ctx, uint8_t topic)
{
    if (ctx == NULL)
    {
        return ARTIE_CAN_ERR_INVALID_ARG;
    }

    for (uint8_t i = 0; i < ctx->psacp_context.subscribed_topic_count; i++)
    {
        if (ctx->psacp_context.subscribed_topics[i] == topic)
        {
            // Remove by swapping with the last element
            ctx->psacp_context.subscribed_topics[i] = ctx->psacp_context.subscribed_topics[ctx->psacp_context.subscribed_topic_count - 1U];
            ctx->psacp_context.subscribed_topic_count--;

            ARTIE_CAN_LOG(ctx, "PSACP: Unsubscribed from topic 0x%02X (total subscriptions: %u)\n", topic, ctx->psacp_context.subscribed_topic_count);

            return ARTIE_CAN_ERR_NONE;
        }
    }

    return ARTIE_CAN_ERR_NO_DATA;
}

artie_can_error_t artie_can_psacp_init_frame(artie_can_frame_t *out, const artie_can_frame_psacp_t *in)
{
    if (out == NULL)
    {
        return ARTIE_CAN_ERR_INVALID_ARG;
    }
    else if (in == NULL)
    {
        return ARTIE_CAN_ERR_INVALID_ARG;
    }
    else if (in->nbytes > ARTIE_CAN_PSACP_MAX_DATA_BYTES)
    {
        return ARTIE_CAN_ERR_INVALID_ARG;
    }

    uint8_t protocol_id = in->high_priority ? ARTIE_CAN_PSACP_HIGH_PROTOCOL_ID : ARTIE_CAN_PSACP_LOW_PROTOCOL_ID;

    out->id = ((uint32_t)protocol_id << (uint32_t)ARTIE_CAN_FRAME_ID_PROTOCOL_LOCATION) |
              ((uint32_t)ARTIE_CAN_PSACP_FRAME_TYPE_PUB << (uint32_t)ARTIE_CAN_FRAME_ID_FRAME_TYPE_LOCATION) |
              ((uint32_t)in->priority << (uint32_t)ARTIE_CAN_FRAME_ID_USER_PRIORITY_LOCATION) |
              ((uint32_t)in->source_address << (uint32_t)ARTIE_CAN_FRAME_ID_SENDER_ADDRESS_LOCATION) |
              ((uint32_t)in->topic << (uint32_t)PSACP_FRAME_ID_TOPIC_LOCATION);

    out->dlc = in->nbytes;
    memcpy(out->data, in->data, in->nbytes);

    return ARTIE_CAN_ERR_NONE;
}

artie_can_error_t artie_can_psacp_parse_frame(const artie_can_frame_t *in, artie_can_frame_psacp_t *out)
{
    if (in == NULL)
    {
        return ARTIE_CAN_ERR_INVALID_ARG;
    }
    else if (out == NULL)
    {
        return ARTIE_CAN_ERR_INVALID_ARG;
    }
    else if (in->dlc > ARTIE_CAN_PSACP_MAX_DATA_BYTES)
    {
        return ARTIE_CAN_ERR_INVALID_ARG;
    }

    uint8_t protocol_id = (uint8_t)((in->id & (uint32_t)ARTIE_CAN_FRAME_ID_PROTOCOL_MASK) >> (uint32_t)ARTIE_CAN_FRAME_ID_PROTOCOL_LOCATION);
    if ((protocol_id != ARTIE_CAN_PSACP_HIGH_PROTOCOL_ID) && (protocol_id != ARTIE_CAN_PSACP_LOW_PROTOCOL_ID))
    {
        return ARTIE_CAN_ERR_INVALID_ARG;
    }

    // Only a single-frame PUB is a whole message. A fragment of a multi-frame message parsed as
    // though it were one would hand the caller 8 bytes of a larger payload as if that were all of
    // it - and, for PUB_START, would include the fragment count byte as though it were data.
    if (_frame_type(in) != ARTIE_CAN_PSACP_FRAME_TYPE_PUB)
    {
        return ARTIE_CAN_ERR_INVALID_ARG;
    }

    out->high_priority = (protocol_id == ARTIE_CAN_PSACP_HIGH_PROTOCOL_ID);
    out->priority = (artie_can_frame_priority_psacp_t)((in->id & (uint32_t)ARTIE_CAN_FRAME_ID_USER_PRIORITY_MASK) >> (uint32_t)ARTIE_CAN_FRAME_ID_USER_PRIORITY_LOCATION);
    out->source_address = (uint8_t)((in->id & (uint32_t)ARTIE_CAN_FRAME_ID_SENDER_ADDRESS_MASK) >> (uint32_t)ARTIE_CAN_FRAME_ID_SENDER_ADDRESS_LOCATION);
    out->topic = (uint8_t)((in->id & (uint32_t)PSACP_FRAME_ID_TOPIC_MASK) >> (uint32_t)PSACP_FRAME_ID_TOPIC_LOCATION);
    out->nbytes = in->dlc;
    memcpy(out->data, in->data, in->dlc);

    return ARTIE_CAN_ERR_NONE;
}

artie_can_error_t artie_can_psacp_publish(artie_can_backend_t *handle, const artie_can_frame_t *frame)
{
    if (handle == NULL)
    {
        return ARTIE_CAN_ERR_INVALID_ARG;
    }
    else if (frame == NULL)
    {
        return ARTIE_CAN_ERR_INVALID_ARG;
    }
    else if (handle->send == NULL)
    {
        return ARTIE_CAN_ERR_INVALID_ARG;
    }
    else if (handle->context == NULL)
    {
        return ARTIE_CAN_ERR_INVALID_ARG;
    }

    uint8_t topic = (uint8_t)((frame->id & (uint32_t)PSACP_FRAME_ID_TOPIC_MASK) >> (uint32_t)PSACP_FRAME_ID_TOPIC_LOCATION);

    ARTIE_CAN_LOG(handle->context, "PSACP: Publishing to topic 0x%02X (%u bytes)\n", topic, frame->dlc);

    artie_can_error_t err = artie_can_send_with_retry(handle, frame);
    if (err != ARTIE_CAN_ERR_NONE)
    {
        ARTIE_CAN_LOG(handle->context, "PSACP: Failed to publish frame, error code %d.\n", err);
        return err;
    }

    // The UDP backend (and hardware backends) do not echo frames back to the sender,
    // so we handle local delivery here: if we are subscribed to this topic (or it is broadcast),
    // invoke the rx_callback as if we had received the message.
    if ((handle->context->protocol_flags & ARTIE_CAN_PROTOCOL_FLAG_PSACP) != 0)
    {
        if (_is_subscribed(&handle->context->psacp_context, topic))
        {
            ARTIE_CAN_LOG(handle->context, "PSACP: Local delivery for topic 0x%02X (node is subscribed)\n", topic);
            handle->context->rx_callback(frame);
        }
    }

    return ARTIE_CAN_ERR_NONE;
}

artie_can_error_t artie_can_psacp_publish_message(artie_can_backend_t *handle, uint8_t topic, const uint8_t *data, uint16_t nbytes, artie_can_frame_priority_psacp_t priority, bool high_priority)
{
    if ((handle == NULL) || (handle->context == NULL) || (handle->send == NULL))
    {
        return ARTIE_CAN_ERR_INVALID_ARG;
    }
    else if ((data == NULL) && (nbytes > 0U))
    {
        return ARTIE_CAN_ERR_INVALID_ARG;
    }
    else if (nbytes > ARTIE_CAN_PSACP_MAX_MESSAGE_SIZE)
    {
        return ARTIE_CAN_ERR_INVALID_ARG;
    }
    else if ((handle->context->protocol_flags & ARTIE_CAN_PROTOCOL_FLAG_PSACP) == 0)
    {
        return ARTIE_CAN_ERR_INVALID_ARG;
    }

    psacp_context_t *ctx = &handle->context->psacp_context;

    // A message that fits in one frame goes out as an ordinary PUB, exactly as it always has.
    if (nbytes <= ARTIE_CAN_PSACP_MAX_DATA_BYTES)
    {
        artie_can_frame_t frame;
        _build_frame(&frame, ARTIE_CAN_PSACP_FRAME_TYPE_PUB, high_priority, (uint8_t)priority,
                     ctx->node_address, topic, 0U, data, (uint8_t)nbytes);
        return artie_can_psacp_publish(handle, &frame);
    }

    // High-priority PSACP arbitrates above BWACP, so a multi-frame burst there would stall block
    // transfers - firmware updates above all. Large payloads belong on the low-priority ID.
    if (high_priority)
    {
        ARTIE_CAN_LOG(handle->context, "PSACP: Refusing a %u byte publish at high priority; multi-frame messages must use low priority.\n", nbytes);
        return ARTIE_CAN_ERR_INVALID_ARG;
    }

    if (ctx->send.active)
    {
        return ARTIE_CAN_ERR_SEND_BUSY;
    }

    uint8_t more_count = 0;
    uint8_t end_bytes = 0;
    _plan_fragmentation(nbytes, &more_count, &end_bytes);

    // The size check above bounds this, but the wire format cannot express a larger count and
    // getting it wrong would corrupt every receiver's state machine rather than fail locally.
    if (more_count > ARTIE_CAN_PSACP_MAX_MORE_FRAMES)
    {
        return ARTIE_CAN_ERR_INVALID_ARG;
    }

    memcpy(ctx->send.data, data, nbytes);
    ctx->send.nbytes = nbytes;
    ctx->send.topic = topic;
    ctx->send.priority = (uint8_t)priority;
    ctx->send.more_count = more_count;
    ctx->send.more_sent = 0;
    ctx->send.start_sent = false;
    ctx->send.deliver_locally = _is_subscribed(ctx, topic);
    ctx->send.active = true;

    ARTIE_CAN_LOG(handle->context, "PSACP: Queued a %u byte publish to topic 0x%02X (%u PUB_MORE frames).\n", nbytes, topic, more_count);

    return ARTIE_CAN_ERR_NONE;
}

bool artie_can_psacp_is_busy(artie_can_backend_t *handle)
{
    if ((handle == NULL) || (handle->context == NULL))
    {
        return false;
    }

    return handle->context->psacp_context.send.active;
}

artie_can_error_t artie_can_psacp_get_message(artie_can_context_t *context, artie_can_psacp_message_t *out)
{
    if ((context == NULL) || (out == NULL))
    {
        return ARTIE_CAN_ERR_INVALID_ARG;
    }

    psacp_context_t *ctx = &context->psacp_context;

    for (uint8_t i = 0; i < ARTIE_CAN_PSACP_REASSEMBLY_SLOTS; i++)
    {
        psacp_reassembly_slot_t *slot = &ctx->slots[i];
        if (slot->state != PSACP_SLOT_COMPLETE)
        {
            continue;
        }

        out->source_address = slot->source_address;
        out->topic = slot->topic;
        out->nbytes = slot->nbytes;
        memcpy(out->data, slot->data, slot->nbytes);

        // Freeing the slot is what lets this (sender, topic) pair start another message.
        slot->state = PSACP_SLOT_FREE;
        slot->nbytes = 0;

        return ARTIE_CAN_ERR_NONE;
    }

    return ARTIE_CAN_ERR_NO_DATA;
}

uint32_t artie_can_psacp_dropped_count(const artie_can_context_t *context)
{
    if (context == NULL)
    {
        return 0U;
    }

    return context->psacp_context.dropped_message_count;
}

/**
 * @brief Find the slot reassembling a message from this (sender, topic) pair, if there is one.
 *
 * Keyed on both fields because CAN arbitration interleaves concurrent publishers to one topic;
 * matching on the topic alone would splice two nodes' fragments into one corrupt message.
 */
static psacp_reassembly_slot_t *_find_slot(psacp_context_t *ctx, uint8_t source_address, uint8_t topic)
{
    for (uint8_t i = 0; i < ARTIE_CAN_PSACP_REASSEMBLY_SLOTS; i++)
    {
        psacp_reassembly_slot_t *slot = &ctx->slots[i];
        if ((slot->state != PSACP_SLOT_FREE) && (slot->source_address == source_address) && (slot->topic == topic))
        {
            return slot;
        }
    }

    return NULL;
}

/** Claim a free slot, or NULL if every one of them is busy. */
static psacp_reassembly_slot_t *_claim_slot(psacp_context_t *ctx)
{
    for (uint8_t i = 0; i < ARTIE_CAN_PSACP_REASSEMBLY_SLOTS; i++)
    {
        if (ctx->slots[i].state == PSACP_SLOT_FREE)
        {
            return &ctx->slots[i];
        }
    }

    return NULL;
}

/** Abandon a partially reassembled message and count it as dropped. */
static void _drop_slot(psacp_context_t *ctx, psacp_reassembly_slot_t *slot)
{
    slot->state = PSACP_SLOT_FREE;
    slot->nbytes = 0;
    ctx->dropped_message_count++;
}

/**
 * @brief Take one fragment of a multi-frame message.
 *
 * Every way a message can be damaged ends with the whole thing discarded rather than delivered
 * short, which is what lets a subscriber trust that what it receives is what was published:
 *
 * - an interior PUB_MORE lost, or frames reordered: the index does not match what was expected
 * - the *last* PUB_MORE lost: fewer PUB_MOREs arrived than PUB_START promised
 * - PUB_START lost: a continuation arrives with no slot open for it
 * - PUB_END lost: the slot ages out in psacp_tick(), or the next PUB_START reclaims it
 *
 * Runs in ISR context, so it does not read the clock - psacp_tick() handles slot ageing.
 */
static void _receive_fragment(artie_can_context_t *context, const artie_can_frame_t *frame, uint8_t frame_type)
{
    psacp_context_t *ctx = &context->psacp_context;
    uint8_t source_address = _frame_source(frame);
    uint8_t topic = _frame_topic(frame);
    psacp_reassembly_slot_t *slot = _find_slot(ctx, source_address, topic);

    if (frame_type == ARTIE_CAN_PSACP_FRAME_TYPE_PUB_START)
    {
        if (frame->dlc != ARTIE_CAN_FRAME_MAX_DATA_LENGTH)
        {
            ctx->dropped_message_count++;
            return;
        }

        uint8_t more_count = frame->data[ARTIE_CAN_PSACP_START_COUNT_OFFSET];
        if (more_count > ARTIE_CAN_PSACP_MAX_MORE_FRAMES)
        {
            ctx->dropped_message_count++;
            return;
        }

        if (slot != NULL)
        {
            // Either the previous message from this publisher never finished, or it finished and
            // has not been collected yet. In both cases the newer message is the one to keep;
            // dropping the older one here is also what stops a lost PUB_END wedging a slot.
            _drop_slot(ctx, slot);
        }
        else
        {
            slot = _claim_slot(ctx);
            if (slot == NULL)
            {
                // Every slot is busy with another publisher. Nothing to reclaim without corrupting
                // someone else's message, so this one is lost.
                ctx->dropped_message_count++;
                return;
            }
        }

        slot->state = PSACP_SLOT_RECEIVING;
        slot->source_address = source_address;
        slot->topic = topic;
        slot->promised_more_count = more_count;
        slot->received_more_count = 0;
        slot->next_expected_index = 0;
        slot->nbytes = ARTIE_CAN_PSACP_START_PAYLOAD_BYTES;
        // Left unequal to nbytes so the next tick sees progress and stamps the slot; until then it
        // cannot age out, because ageing only ever fires a whole timeout after a stamp.
        slot->last_seen_nbytes = 0;
        slot->last_activity_ms = 0;
        memcpy(slot->data, &frame->data[ARTIE_CAN_PSACP_START_COUNT_OFFSET + 1U], ARTIE_CAN_PSACP_START_PAYLOAD_BYTES);
        return;
    }

    // Everything below is a continuation, which is only meaningful with a message already open.
    if ((slot == NULL) || (slot->state != PSACP_SLOT_RECEIVING))
    {
        ctx->dropped_message_count++;
        return;
    }

    if (frame_type == ARTIE_CAN_PSACP_FRAME_TYPE_PUB_MORE)
    {
        if ((frame->dlc != ARTIE_CAN_FRAME_MAX_DATA_LENGTH) ||
            (_frame_index(frame) != slot->next_expected_index) ||
            (slot->received_more_count >= slot->promised_more_count) ||
            ((slot->nbytes + ARTIE_CAN_PSACP_MAX_DATA_BYTES) > ARTIE_CAN_PSACP_SLOT_BUFFER_SIZE))
        {
            _drop_slot(ctx, slot);
            return;
        }

        memcpy(&slot->data[slot->nbytes], frame->data, ARTIE_CAN_PSACP_MAX_DATA_BYTES);
        slot->nbytes = (uint16_t)(slot->nbytes + ARTIE_CAN_PSACP_MAX_DATA_BYTES);
        slot->received_more_count++;
        // The index is 6 bits on the wire, so it wraps at 64 - which only matters for a message
        // using the entire index space.
        slot->next_expected_index = (uint8_t)((slot->next_expected_index + 1U) % (ARTIE_CAN_PSACP_MAX_MORE_FRAMES));
        return;
    }

    if (frame_type == ARTIE_CAN_PSACP_FRAME_TYPE_PUB_END)
    {
        // This is the check that catches a lost *final* PUB_MORE. PUB_END carries no index, so
        // without the count PUB_START promised there would be nothing to compare against and the
        // message would be delivered 8 bytes short.
        if ((slot->received_more_count != slot->promised_more_count) ||
            (frame->dlc == 0U) ||
            (frame->dlc > ARTIE_CAN_PSACP_MAX_DATA_BYTES) ||
            ((slot->nbytes + frame->dlc) > ARTIE_CAN_PSACP_SLOT_BUFFER_SIZE))
        {
            _drop_slot(ctx, slot);
            return;
        }

        memcpy(&slot->data[slot->nbytes], frame->data, frame->dlc);
        slot->nbytes = (uint16_t)(slot->nbytes + frame->dlc);
        slot->state = PSACP_SLOT_COMPLETE;
    }
}

// !! Make sure all code in this function interacts with the rest of the code in a re-entrant manner !!
void psacp_receive_in_isr(artie_can_context_t *context, const artie_can_frame_t *frame)
{
    if ((context->protocol_flags & ARTIE_CAN_PROTOCOL_FLAG_PSACP) == 0)
    {
        // This node is not configured to use PSACP, ignore the frame.
        ARTIE_CAN_LOG(context, "PSACP: Received PSACP frame but this node is not configured for PSACP, ignoring.\n");
        return;
    }

    uint8_t topic = _frame_topic(frame);

    if (!_is_subscribed(&context->psacp_context, topic))
    {
        ARTIE_CAN_LOG(context, "PSACP: Received frame for topic 0x%02X but not subscribed, ignoring.\n", topic);
        return;
    }

    uint8_t frame_type = _frame_type(frame);

    if (frame_type == ARTIE_CAN_PSACP_FRAME_TYPE_PUB)
    {
        // A whole message in one frame, which is the common case and stays on the fast path: the
        // callback fires here rather than waiting for a tick, exactly as it did before
        // fragmentation existed.
        ARTIE_CAN_LOG(context, "PSACP: Received frame for topic 0x%02X, calling callback.\n", topic);
        context->rx_callback(frame);
        return;
    }

    if ((frame_type == ARTIE_CAN_PSACP_FRAME_TYPE_PUB_START) ||
        (frame_type == ARTIE_CAN_PSACP_FRAME_TYPE_PUB_MORE) ||
        (frame_type == ARTIE_CAN_PSACP_FRAME_TYPE_PUB_END))
    {
        // Reassembly happens here rather than in the tick because there is nowhere to stage an
        // unbounded run of frames otherwise: PSACP has no ACK, so fragments arrive back to back
        // and a single staging slot would lose all but the last. The work is a bounds check and a
        // memcpy, no heavier than the subscription scan above.
        _receive_fragment(context, frame, frame_type);
        return;
    }

    // A frame type this build does not know about. Ignoring it is what keeps a node that predates
    // a future PSACP extension from handing a fragment to an application as though it were whole.
    ARTIE_CAN_LOG(context, "PSACP: Received unknown frame type 0x%02X for topic 0x%02X, ignoring.\n", frame_type, topic);
}

/**
 * @brief Emit the next few frames of a multi-frame publish.
 *
 * Bounded by ARTIE_CAN_PSACP_FRAMES_PER_TICK so that one call cannot monopolise the tick, which
 * every other protocol's state machine shares.
 */
static artie_can_error_t _send_pending_frames(artie_can_backend_t *handle)
{
    psacp_context_t *ctx = &handle->context->psacp_context;
    artie_can_error_t err = ARTIE_CAN_ERR_NONE;

    for (uint8_t sent = 0; (sent < ARTIE_CAN_PSACP_FRAMES_PER_TICK) && ctx->send.active; sent++)
    {
        artie_can_frame_t frame;

        if (!ctx->send.start_sent)
        {
            uint8_t start_data[ARTIE_CAN_FRAME_MAX_DATA_LENGTH];
            start_data[ARTIE_CAN_PSACP_START_COUNT_OFFSET] = ctx->send.more_count;
            memcpy(&start_data[ARTIE_CAN_PSACP_START_COUNT_OFFSET + 1U], ctx->send.data, ARTIE_CAN_PSACP_START_PAYLOAD_BYTES);

            _build_frame(&frame, ARTIE_CAN_PSACP_FRAME_TYPE_PUB_START, false, ctx->send.priority,
                         ctx->node_address, ctx->send.topic, 0U, start_data, ARTIE_CAN_FRAME_MAX_DATA_LENGTH);
        }
        else if (ctx->send.more_sent < ctx->send.more_count)
        {
            uint16_t offset = (uint16_t)(ARTIE_CAN_PSACP_START_PAYLOAD_BYTES +
                                         ((uint16_t)ctx->send.more_sent * ARTIE_CAN_PSACP_MAX_DATA_BYTES));

            _build_frame(&frame, ARTIE_CAN_PSACP_FRAME_TYPE_PUB_MORE, false, ctx->send.priority,
                         ctx->node_address, ctx->send.topic,
                         (uint8_t)(ctx->send.more_sent % ARTIE_CAN_PSACP_MAX_MORE_FRAMES),
                         &ctx->send.data[offset], ARTIE_CAN_PSACP_MAX_DATA_BYTES);
        }
        else
        {
            uint16_t offset = (uint16_t)(ARTIE_CAN_PSACP_START_PAYLOAD_BYTES +
                                         ((uint16_t)ctx->send.more_count * ARTIE_CAN_PSACP_MAX_DATA_BYTES));

            _build_frame(&frame, ARTIE_CAN_PSACP_FRAME_TYPE_PUB_END, false, ctx->send.priority,
                         ctx->node_address, ctx->send.topic, 0U,
                         &ctx->send.data[offset], (uint8_t)(ctx->send.nbytes - offset));
        }

        artie_can_error_t send_err = artie_can_send_with_retry(handle, &frame);
        if (send_err != ARTIE_CAN_ERR_NONE)
        {
            // The bus would not take this frame. There is no retransmission in PSACP, so the
            // message is abandoned - a receiver will see the gap and drop its partial copy.
            ARTIE_CAN_LOG(handle->context, "PSACP: Abandoning multi-frame publish, send failed with %d.\n", send_err);
            ctx->send.active = false;
            return send_err;
        }

        // Advance only after the frame is actually away, so a failure cannot skip a fragment.
        if (!ctx->send.start_sent)
        {
            ctx->send.start_sent = true;
        }
        else if (ctx->send.more_sent < ctx->send.more_count)
        {
            ctx->send.more_sent++;
        }
        else
        {
            // PUB_END is away, so the message is complete.
            if (ctx->send.deliver_locally)
            {
                // Nothing echoes our own frames back to us, so a node subscribed to a topic it
                // publishes on has to deliver to itself. Stage it as a completed slot so that it
                // arrives by the same route as a message from anyone else.
                psacp_reassembly_slot_t *slot = _claim_slot(ctx);
                if (slot != NULL)
                {
                    slot->state = PSACP_SLOT_COMPLETE;
                    slot->source_address = ctx->node_address;
                    slot->topic = ctx->send.topic;
                    slot->nbytes = ctx->send.nbytes;
                    memcpy(slot->data, ctx->send.data, ctx->send.nbytes);
                }
                else
                {
                    ctx->dropped_message_count++;
                }
            }

            ctx->send.active = false;
        }
    }

    return err;
}

/**
 * @brief Note which partial messages are still making progress, and discard those that are not.
 *
 * Doubles as the slots' clock. The ISR that accepts fragments has no access to get_ms(), so
 * progress is inferred here by watching nbytes move between ticks; a slot only starts running down
 * its timeout once it has stopped growing.
 */
static void _age_out_slots(artie_can_backend_t *handle)
{
    psacp_context_t *ctx = &handle->context->psacp_context;

    // Only partial messages age out, and most of the time there are none. Check for one before
    // reading the clock: this runs on every tick of every PSACP node, and get_ms() is the
    // expensive part - on an OS it is a system call, and the tick loop is meant to be tight
    // enough for RTACP's 10 ms ACK budget.
    bool any_partial = false;
    for (uint8_t i = 0; i < ARTIE_CAN_PSACP_REASSEMBLY_SLOTS; i++)
    {
        if (ctx->slots[i].state == PSACP_SLOT_RECEIVING)
        {
            any_partial = true;
            break;
        }
    }

    if (!any_partial)
    {
        return;
    }

    uint64_t now_ms = handle->get_ms();

    for (uint8_t i = 0; i < ARTIE_CAN_PSACP_REASSEMBLY_SLOTS; i++)
    {
        psacp_reassembly_slot_t *slot = &ctx->slots[i];

        // A COMPLETE slot is holding a whole, valid message and is waiting on the application to
        // collect it, however long that takes.
        if (slot->state != PSACP_SLOT_RECEIVING)
        {
            continue;
        }

        if (slot->nbytes != slot->last_seen_nbytes)
        {
            slot->last_seen_nbytes = slot->nbytes;
            slot->last_activity_ms = now_ms;
            continue;
        }

        if ((now_ms - slot->last_activity_ms) >= (uint64_t)ARTIE_CAN_PSACP_REASSEMBLY_TIMEOUT_MS)
        {
            ARTIE_CAN_LOG(handle->context, "PSACP: Reassembly of topic 0x%02X from 0x%02X timed out, dropping.\n", slot->topic, slot->source_address);
            _drop_slot(ctx, slot);
        }
    }
}

artie_can_error_t psacp_tick(artie_can_backend_t *handle)
{
    if (handle == NULL)
    {
        return ARTIE_CAN_ERR_INVALID_ARG;
    }
    else if (handle->context == NULL)
    {
        return ARTIE_CAN_ERR_INVALID_ARG;
    }

    artie_can_error_t err = ARTIE_CAN_ERR_NONE;

    if (handle->context->psacp_context.send.active)
    {
        err = _send_pending_frames(handle);
    }

    if (handle->get_ms != NULL)
    {
        _age_out_slots(handle);
    }

    return err;
}
