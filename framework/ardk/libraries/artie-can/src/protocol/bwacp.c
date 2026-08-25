/**
 * @file bwacp.c
 * @brief Implementation of BWACP (Block Write Artie CAN Protocol).
 *
 */

#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#include "backend.h"
#include "bwacp.h"
#include "bwacp_context.h"
#include "context.h"
#include "err.h"
#include "frame.h"
#include "log.h"
#include "util.h"

// OpenPGP CRC-24 parameters
#define CRC24_INIT 0xB704CE
#define CRC24_POLY 0x1864CFB

/**
 * Compute OpenPGP CRC-24 checksum.
 * @param data Pointer to input data
 * @param len  Length of input data in bytes
 * @return 24-bit CRC value (stored in 32-bit integer)
 */
static uint32_t _crc24_openpgp(const uint8_t *data, size_t len)
{
    uint32_t crc = CRC24_INIT;

    for (size_t i = 0; i < len; i++)
    {
        crc ^= ((uint32_t)data[i]) << 16; // Align byte to top 8 bits of 24-bit CRC
        for (int j = 0; j < 8; j++)
        {
            crc <<= 1;
            if (crc & 0x1000000)
            { // If 25th bit set
                crc ^= CRC24_POLY;
            }
        }
    }
    return crc & 0xFFFFFF; // Mask to 24 bits
}

/**
 * @brief Check if this node should accept a frame based on addressing.
 */
static bool _should_accept_frame(bwacp_context_t *ctx, uint8_t target_address, uint8_t target_class)
{
    // Check if addressed to us specifically
    if (target_address == ctx->node_address)
    {
        return true;
    }

    // Check if multicast and we match the class
    if (target_address == ARTIE_CAN_BWACP_MULTICAST_ADDRESS)
    {
        if ((target_class & ctx->node_class) != 0)
        {
            return true;
        }
    }

    return false;
}

/**
 * @brief Send an ACK frame.
 */
static artie_can_error_t _send_ack(artie_can_backend_t *handle, uint8_t target_address)
{
    artie_can_frame_t frame = {0};
    bwacp_context_t *ctx = &handle->context->bwacp_context;

    // Build frame ID with ACK bit set
    frame.id = ((uint32_t)ARTIE_CAN_BWACP_PROTOCOL_ID << ARTIE_CAN_FRAME_ID_PROTOCOL_LOCATION) |
               ((uint32_t)ARTIE_CAN_FRAME_TYPE_BWACP_ACK_NACK << ARTIE_CAN_FRAME_ID_FRAME_TYPE_LOCATION) |
               ((uint32_t)ARTIE_CAN_FRAME_PRIORITY_BWACP_HIGH << ARTIE_CAN_FRAME_ID_USER_PRIORITY_LOCATION) |
               ((uint32_t)ctx->node_address << ARTIE_CAN_FRAME_ID_SENDER_ADDRESS_LOCATION) |
               ((uint32_t)target_address << ARTIE_CAN_FRAME_ID_TARGET_ADDRESS_LOCATION) |
               (1U << BWACP_FRAME_ID_ACK_REPEAT_LOCATION); // ACK bit set

    frame.dlc = 0; // ACK frames have no data

    ARTIE_CAN_LOG(handle->context, "BWACP: Sending ACK frame to 0x%02X\n", target_address);

    return artie_can_send_with_retry(handle, &frame);
}

/**
 * @brief Send a NACK frame.
 */
static artie_can_error_t _send_nack(artie_can_backend_t *handle, uint8_t target_address)
{
    artie_can_frame_t frame = {0};
    bwacp_context_t *ctx = &handle->context->bwacp_context;

    // Build frame ID with ACK bit clear (NACK)
    frame.id = ((uint32_t)ARTIE_CAN_BWACP_PROTOCOL_ID << ARTIE_CAN_FRAME_ID_PROTOCOL_LOCATION) |
               ((uint32_t)ARTIE_CAN_FRAME_TYPE_BWACP_ACK_NACK << ARTIE_CAN_FRAME_ID_FRAME_TYPE_LOCATION) |
               ((uint32_t)ARTIE_CAN_FRAME_PRIORITY_BWACP_HIGH << ARTIE_CAN_FRAME_ID_USER_PRIORITY_LOCATION) |
               ((uint32_t)ctx->node_address << ARTIE_CAN_FRAME_ID_SENDER_ADDRESS_LOCATION) |
               ((uint32_t)target_address << ARTIE_CAN_FRAME_ID_TARGET_ADDRESS_LOCATION);
    // ACK bit not set (0) means NACK

    frame.dlc = 0; // NACK frames have no data

    ARTIE_CAN_LOG(handle->context, "BWACP: Sending NACK frame to 0x%02X\n", target_address);

    return artie_can_send_with_retry(handle, &frame);
}

/**
 * @brief Whether @p dlc more bytes still fit in the receive buffer at the current write position.
 *
 * The write position is (receive_address + receive_bytes_written), and receive_address comes
 * straight off the wire in the READY frame, so the arithmetic subtracts from the buffer size
 * rather than adding up to it: a hostile or buggy sender advertising an address near UINT32_MAX
 * would otherwise wrap the sum around and slip past an addition-based bounds check.
 */
static bool _receive_fits(const bwacp_context_t *ctx, uint8_t dlc)
{
    if (ctx->receive_buffer == NULL)
    {
        return false;
    }
    if (ctx->receive_address > ctx->receive_buffer_size)
    {
        return false;
    }

    uint32_t remaining = ctx->receive_buffer_size - ctx->receive_address;
    if (ctx->receive_bytes_written > remaining)
    {
        return false;
    }

    return (uint32_t)dlc <= (remaining - ctx->receive_bytes_written);
}

/**
 * @brief Drop out of a reception whose data will not fit in the receive buffer.
 *
 * Too small a buffer (or none at all) is not something a retransmission can fix - the same bytes
 * would arrive again and still not fit - so NACKing to ask for a repeat only burns the repeat
 * budget, and ACKing as if the bytes had been stored leaves the sender believing in a transfer
 * this node has holes in. BWACP has no abort frame, so the only way to say "count me out" is to
 * stop answering: going back to IDLE and forgetting the sender makes the ISR filter discard the
 * rest of the transfer, and the sender's existing repeat-then-blacklist path takes it from there.
 * A multicast carries on with the receivers that do have room; a unicast fails with a timeout.
 */
static void _abort_receive_no_space(artie_can_backend_t *handle)
{
    bwacp_context_t *ctx = &handle->context->bwacp_context;

    ARTIE_CAN_LOG(handle->context, "BWACP: Receive buffer cannot hold this transfer (address=%u, written=%u, size=%u); leaving the transfer\n",
                  ctx->receive_address, ctx->receive_bytes_written, ctx->receive_buffer_size);

    ctx->receive_bytes_written = 0;
    ctx->receive_accepted_any_frame = false;
    ctx->transfer_invalidated = false;
    ctx->sending_node_address = 0xFF;
    ctx->state = BWACP_STATE_IDLE;
}

/**
 * @brief Send a READY frame.
 */
static artie_can_error_t _send_ready(artie_can_backend_t *handle, const uint8_t *payload, uint32_t payload_size, uint32_t address, uint8_t target_address, uint8_t target_class, artie_can_frame_priority_bwacp_t priority)
{
    artie_can_frame_t frame = {0};
    bwacp_context_t *ctx = &handle->context->bwacp_context;

    // Calculate CRC24 over the payload
    uint32_t crc24 = _crc24_openpgp(payload, payload_size);
    ctx->send_crc24 = crc24;

    // Build frame ID
    frame.id = ((uint32_t)ARTIE_CAN_BWACP_PROTOCOL_ID << ARTIE_CAN_FRAME_ID_PROTOCOL_LOCATION) |
               ((uint32_t)ARTIE_CAN_FRAME_TYPE_BWACP_READY << ARTIE_CAN_FRAME_ID_FRAME_TYPE_LOCATION) |
               ((uint32_t)priority << ARTIE_CAN_FRAME_ID_USER_PRIORITY_LOCATION) |
               ((uint32_t)ctx->node_address << ARTIE_CAN_FRAME_ID_SENDER_ADDRESS_LOCATION) |
               ((uint32_t)target_address << ARTIE_CAN_FRAME_ID_TARGET_ADDRESS_LOCATION) |
               ((uint32_t)target_class << BWACP_FRAME_ID_CLASS_LOCATION);

    // Data: [3 bytes CRC24][4 bytes address][1 byte first stuffing byte]
    frame.data[BWACP_READY_DATA_CRC24_BYTE0] = (crc24 >> BWACP_CRC24_SHIFT_BYTE0) & 0xFF;
    frame.data[BWACP_READY_DATA_CRC24_BYTE1] = (crc24 >> BWACP_CRC24_SHIFT_BYTE1) & 0xFF;
    frame.data[BWACP_READY_DATA_CRC24_BYTE2] = (crc24 >> BWACP_CRC24_SHIFT_BYTE2) & 0xFF;
    frame.data[BWACP_READY_DATA_ADDRESS_BYTE0] = (address >> BWACP_SHIFT_BYTE0) & 0xFF;
    frame.data[BWACP_READY_DATA_ADDRESS_BYTE1] = (address >> BWACP_SHIFT_BYTE1) & 0xFF;
    frame.data[BWACP_READY_DATA_ADDRESS_BYTE2] = (address >> BWACP_SHIFT_BYTE2) & 0xFF;
    frame.data[BWACP_READY_DATA_ADDRESS_BYTE3] = (address >> BWACP_SHIFT_BYTE3) & 0xFF;
    frame.data[BWACP_READY_DATA_STUFFING] = 0x00; // First stuffing byte
    frame.dlc = 8; // 3-byte CRC24 + 4-byte address + 1-byte stuffing

    ARTIE_CAN_LOG(handle->context, "BWACP: Sending READY frame (addr=0x%08X, size=%u)\n", address, payload_size);
    return artie_can_send_with_retry(handle, &frame);
}

/**
 * @brief Send a DATA frame carrying the payload at @p offset with parity @p parity.
 *
 * The frame to transmit is passed in explicitly rather than read from the send cursor so that
 * a repeat can be rebuilt from ctx->last_sent_* without rewinding (and then having to restore)
 * ctx->send_payload_offset / ctx->send_parity.
 */
static artie_can_error_t _send_data(artie_can_backend_t *handle, uint32_t offset, bool parity, bool is_repeat)
{
    artie_can_frame_t frame = {0};
    bwacp_context_t *ctx = &handle->context->bwacp_context;

    // Build frame ID
    frame.id = ((uint32_t)ARTIE_CAN_BWACP_PROTOCOL_ID << ARTIE_CAN_FRAME_ID_PROTOCOL_LOCATION) |
               ((uint32_t)ARTIE_CAN_FRAME_TYPE_BWACP_DATA << ARTIE_CAN_FRAME_ID_FRAME_TYPE_LOCATION) |
               ((uint32_t)ARTIE_CAN_FRAME_PRIORITY_BWACP_LOW << ARTIE_CAN_FRAME_ID_USER_PRIORITY_LOCATION) |
               ((uint32_t)ctx->node_address << ARTIE_CAN_FRAME_ID_SENDER_ADDRESS_LOCATION) |
               ((uint32_t)ctx->send_target_address << ARTIE_CAN_FRAME_ID_TARGET_ADDRESS_LOCATION) |
               ((uint32_t)ctx->send_target_class << BWACP_FRAME_ID_CLASS_LOCATION);

    // Set parity bit
    frame.id |= ((parity ? 1U : 0U) << BWACP_FRAME_ID_PARITY_LOCATION);

    // Set repeat bit
    if (is_repeat)
    {
        frame.id |= (1U << BWACP_FRAME_ID_ACK_REPEAT_LOCATION);
    }

    // Copy up to 8 bytes of payload. The DLC is derived from the offset being sent, so a repeat of
    // a short final frame carries the same number of bytes as the original did.
    uint32_t bytes_remaining = ctx->send_payload_size - offset;
    frame.dlc = (bytes_remaining > 8) ? 8 : (uint8_t)bytes_remaining;
    memcpy(frame.data, &ctx->send_payload[offset], frame.dlc);

    ARTIE_CAN_LOG(handle->context, "BWACP: Sending DATA frame (offset=%u, dlc=%u, parity=%d, repeat=%d)\n", offset, frame.dlc, parity, is_repeat);

    return artie_can_send_with_retry(handle, &frame);
}

/**
 * @brief Send a COMPLETE frame.
 */
static artie_can_error_t _send_complete(artie_can_backend_t *handle)
{
    artie_can_frame_t frame = {0};
    bwacp_context_t *ctx = &handle->context->bwacp_context;

    // Build frame ID
    frame.id = ((uint32_t)ARTIE_CAN_BWACP_PROTOCOL_ID << ARTIE_CAN_FRAME_ID_PROTOCOL_LOCATION) |
               ((uint32_t)ARTIE_CAN_FRAME_TYPE_BWACP_COMPLETE << ARTIE_CAN_FRAME_ID_FRAME_TYPE_LOCATION) |
               ((uint32_t)ARTIE_CAN_FRAME_PRIORITY_BWACP_MEDIUM << ARTIE_CAN_FRAME_ID_USER_PRIORITY_LOCATION) |
               ((uint32_t)ctx->node_address << ARTIE_CAN_FRAME_ID_SENDER_ADDRESS_LOCATION) |
               ((uint32_t)ctx->send_target_address << ARTIE_CAN_FRAME_ID_TARGET_ADDRESS_LOCATION) |
               ((uint32_t)ctx->send_target_class << BWACP_FRAME_ID_CLASS_LOCATION);

    frame.dlc = 0; // COMPLETE frames have no data

    ARTIE_CAN_LOG(handle->context, "BWACP: Sending COMPLETE frame\n");
    return artie_can_send_with_retry(handle, &frame);
}

/**
 * @brief Process a READY frame received in ISR.
 */
static void _process_ready_frame_from_isr(artie_can_context_t *context, const artie_can_frame_t *frame)
{
    bwacp_context_t *ctx = &context->bwacp_context;

    // Check for ISR lockout
    if ((ctx->isr_flags & BWACP_ISR_FLAG_READY_RECEIVED) != 0)
    {
        return;
    }

    // If we are already receiving a bulk transfer from another source,
    // ignore this READY frame (BWACP does not support concurrent transfers to the same node)
    if (ctx->state == BWACP_STATE_RECEIVING)
    {
        return;
    }

    // Extract target address and class
    uint8_t target_address = (uint8_t)((frame->id & ARTIE_CAN_FRAME_ID_TARGET_ADDRESS_MASK) >> ARTIE_CAN_FRAME_ID_TARGET_ADDRESS_LOCATION);
    uint8_t target_class = (uint8_t)((frame->id & BWACP_FRAME_ID_CLASS_MASK) >> BWACP_FRAME_ID_CLASS_LOCATION);

    // Check if we should accept this frame
    if (!_should_accept_frame(ctx, target_address, target_class))
    {
        return;
    }

    // Copy frame to context for main thread processing
    memcpy(&ctx->received_ready_frame, frame, sizeof(artie_can_frame_t));

    // Set the address of the node we are receiving from
    ctx->sending_node_address = (uint8_t)((frame->id & ARTIE_CAN_FRAME_ID_SENDER_ADDRESS_MASK) >> ARTIE_CAN_FRAME_ID_SENDER_ADDRESS_LOCATION);

    // Set flag for main thread
    atomic_fetch_or(&ctx->isr_flags, (uint32_t)BWACP_ISR_FLAG_READY_RECEIVED);
}

/**
 * @brief Process a DATA frame received in ISR.
 */
static void _process_data_frame_from_isr(artie_can_context_t *context, const artie_can_frame_t *frame)
{
    bwacp_context_t *ctx = &context->bwacp_context;

    // Check for ISR lockout
    if ((ctx->isr_flags & BWACP_ISR_FLAG_DATA_RECEIVED) != 0)
    {
        return;
    }

    // Check target address
    uint8_t target_address = (uint8_t)((frame->id & ARTIE_CAN_FRAME_ID_TARGET_ADDRESS_MASK) >> ARTIE_CAN_FRAME_ID_TARGET_ADDRESS_LOCATION);
    uint8_t target_class = (uint8_t)((frame->id & BWACP_FRAME_ID_CLASS_MASK) >> BWACP_FRAME_ID_CLASS_LOCATION);

    if (!_should_accept_frame(ctx, target_address, target_class))
    {
        return;
    }

    // Check that we are supposed to be receiving from this node
    uint8_t sending_node_address = (uint8_t)((frame->id & ARTIE_CAN_FRAME_ID_SENDER_ADDRESS_MASK) >> ARTIE_CAN_FRAME_ID_SENDER_ADDRESS_LOCATION);
    if (sending_node_address != ctx->sending_node_address)
    {
        return;
    }

    // Copy frame to context for main thread processing (parity checking will be done in main thread)
    memcpy(&ctx->received_data_frame, frame, sizeof(artie_can_frame_t));

    // Set flag for main thread
    atomic_fetch_or(&ctx->isr_flags, (uint32_t)BWACP_ISR_FLAG_DATA_RECEIVED);
}

/**
 * @brief Process a COMPLETE frame received in ISR.
 */
static void _process_complete_frame_from_isr(artie_can_context_t *context, const artie_can_frame_t *frame)
{
    bwacp_context_t *ctx = &context->bwacp_context;

    // Check for ISR lockout
    if ((ctx->isr_flags & BWACP_ISR_FLAG_COMPLETE_RECEIVED) != 0)
    {
        return;
    }

    // Check target address
    uint8_t target_address = (uint8_t)((frame->id & ARTIE_CAN_FRAME_ID_TARGET_ADDRESS_MASK) >> ARTIE_CAN_FRAME_ID_TARGET_ADDRESS_LOCATION);
    uint8_t target_class = (uint8_t)((frame->id & BWACP_FRAME_ID_CLASS_MASK) >> BWACP_FRAME_ID_CLASS_LOCATION);

    if (!_should_accept_frame(ctx, target_address, target_class))
    {
        return;
    }

    // Check that we are supposed to be receiving from this node
    uint8_t sending_node_address = (uint8_t)((frame->id & ARTIE_CAN_FRAME_ID_SENDER_ADDRESS_MASK) >> ARTIE_CAN_FRAME_ID_SENDER_ADDRESS_LOCATION);
    if (sending_node_address != ctx->sending_node_address)
    {
        return;
    }

    // Copy frame to context for main thread processing
    memcpy(&ctx->received_complete_frame, frame, sizeof(artie_can_frame_t));

    ARTIE_CAN_LOG(context, "BWACP: COMPLETE frame received\n");

    // Set flag
    atomic_fetch_or(&ctx->isr_flags, (uint32_t)BWACP_ISR_FLAG_COMPLETE_RECEIVED);
}

/**
 * @brief Process an ACK/NACK frame (for senders) received in ISR.
 */
static void _process_ack_nack_frame_from_isr(artie_can_context_t *context, const artie_can_frame_t *frame)
{
    bwacp_context_t *ctx = &context->bwacp_context;

    // Check if addressed to us
    uint8_t target_address = (uint8_t)((frame->id & ARTIE_CAN_FRAME_ID_TARGET_ADDRESS_MASK) >> ARTIE_CAN_FRAME_ID_TARGET_ADDRESS_LOCATION);
    if (target_address != ctx->node_address)
    {
        return;
    }

    // Extract sender address
    uint8_t sender_address = (uint8_t)((frame->id & ARTIE_CAN_FRAME_ID_SENDER_ADDRESS_MASK) >> ARTIE_CAN_FRAME_ID_SENDER_ADDRESS_LOCATION);

    // Check if this node is blacklisted
    if ((ctx->blacklisted_nodes_bitmap & (1ULL << sender_address)) != 0)
    {
        // Node is blacklisted, ignore their ACK/NACK
        return;
    }

    // Check if this is an ACK or NACK
    bool is_ack = (frame->id & BWACP_FRAME_ID_ACK_REPEAT_MASK) != 0;

    if (is_ack)
    {
        // Check if we've already received an ACK from this node for this frame
        if ((ctx->ack_received_bitmap & (1ULL << sender_address)) == 0)
        {
            // Mark this node as having ACKed
            ctx->ack_received_bitmap |= (1ULL << sender_address);

            // Atomically increment received ack count
            atomic_fetch_add(&ctx->received_ack_count, 1);
            ARTIE_CAN_LOG(context, "BWACP: ACK received from node 0x%02X (%u/%u)\n", sender_address, ctx->received_ack_count, ctx->expected_ack_count);
        }
    }
    else
    {
        // Atomically increment received nack count and set flag to repeat last data frame
        atomic_fetch_add(&ctx->received_nack_count, 1);
        ctx->need_repeat_data_frame = true;
        ARTIE_CAN_LOG(context, "BWACP: NACK received from node 0x%02X, will repeat last DATA frame\n", sender_address);
    }
}

/**
 * @brief Process READY frame received in ISR (main thread handler).
 */
static artie_can_error_t _process_ready_received(artie_can_backend_t *handle)
{
    bwacp_context_t *ctx = &handle->context->bwacp_context;

    // Extract data from received READY frame
    artie_can_frame_t *frame = &ctx->received_ready_frame;

    // Extract sender address
    ctx->receive_sender_address = (uint8_t)((frame->id & ARTIE_CAN_FRAME_ID_SENDER_ADDRESS_MASK) >> ARTIE_CAN_FRAME_ID_SENDER_ADDRESS_LOCATION);

    // Extract CRC24
    ctx->receive_crc24 = ((uint32_t)frame->data[BWACP_READY_DATA_CRC24_BYTE0] << BWACP_CRC24_SHIFT_BYTE0) |
                         ((uint32_t)frame->data[BWACP_READY_DATA_CRC24_BYTE1] << BWACP_CRC24_SHIFT_BYTE1) |
                         ((uint32_t)frame->data[BWACP_READY_DATA_CRC24_BYTE2] << BWACP_CRC24_SHIFT_BYTE2);

    // Extract address
    ctx->receive_address = ((uint32_t)frame->data[BWACP_READY_DATA_ADDRESS_BYTE0] << BWACP_SHIFT_BYTE0) |
                           ((uint32_t)frame->data[BWACP_READY_DATA_ADDRESS_BYTE1] << BWACP_SHIFT_BYTE1) |
                           ((uint32_t)frame->data[BWACP_READY_DATA_ADDRESS_BYTE2] << BWACP_SHIFT_BYTE2) |
                           ((uint32_t)frame->data[BWACP_READY_DATA_ADDRESS_BYTE3] << BWACP_SHIFT_BYTE3);

    // Reset receive state
    ctx->receive_bytes_written = 0;
    ctx->receive_expected_parity = false;
    ctx->receive_accepted_any_frame = false;
    ctx->state = BWACP_STATE_RECEIVING;
    ctx->last_packet_ms = handle->get_ms();
    ctx->transfer_invalidated = false;

    ARTIE_CAN_LOG(handle->context, "BWACP: READY frame received (addr=0x%08X, CRC=0x%06X); sending ACK and setting state to RECEIVING\n", ctx->receive_address, ctx->receive_crc24);

    // Send ACK to sender
    artie_can_error_t err = _send_ack(handle, ctx->receive_sender_address);

    atomic_fetch_and(&ctx->isr_flags, ~((uint32_t)BWACP_ISR_FLAG_READY_RECEIVED));
    return err;
}

/**
 * @brief Handle DATA frame when in RECEIVE_IN_ERROR state.
 */
static artie_can_error_t _handle_data_received_in_error(artie_can_backend_t *handle)
{
    bwacp_context_t *ctx = &handle->context->bwacp_context;

    ARTIE_CAN_LOG(handle->context, "BWACP: In error state, sending ACK for DATA frame\n");
    return _send_ack(handle, ctx->receive_sender_address);
}

/**
 * @brief Handle DATA frame when in EXPECT_REPEAT state.
 */
static artie_can_error_t _handle_data_expect_repeat(artie_can_backend_t *handle, artie_can_frame_t *frame)
{
    bwacp_context_t *ctx = &handle->context->bwacp_context;
    artie_can_error_t err = ARTIE_CAN_ERR_NONE;

    // Extract parity and repeat flag from frame
    bool frame_parity = (frame->id & BWACP_FRAME_ID_PARITY_MASK) != 0;
    bool is_repeat = (frame->id & BWACP_FRAME_ID_ACK_REPEAT_MASK) != 0;

    if (!is_repeat)
    {
        // Protocol violation - expected a repeat but got a fresh frame
        ARTIE_CAN_LOG(handle->context, "BWACP: Expected repeat frame but got fresh frame; entering error state\n");
        ctx->transfer_invalidated = true;
        ctx->state = BWACP_STATE_RECEIVE_IN_ERROR;
        return _send_ack(handle, ctx->receive_sender_address);
    }

    // This is a repeat frame - check parity
    bool parity_correct = (frame_parity == ctx->receive_expected_parity);

    if (!parity_correct && ctx->receive_accepted_any_frame)
    {
        // As in _handle_data_receiving: a repeat carrying the parity we already consumed is a
        // duplicate of the last accepted frame, not a protocol error. We still need the frame we
        // NACKed, so re-send the NACK and stay in EXPECT_REPEAT rather than invalidating the transfer.
        ARTIE_CAN_LOG(handle->context, "BWACP: Duplicate repeat while expecting repeat; re-sending NACK\n");
        return _send_nack(handle, ctx->receive_sender_address);
    }

    if (!parity_correct)
    {
        // Repeat still has wrong parity and we have nothing to have duplicated - give up and enter error state
        ARTIE_CAN_LOG(handle->context, "BWACP: Repeat frame still has parity error; entering error state\n");
        ctx->transfer_invalidated = true;
        ctx->state = BWACP_STATE_RECEIVE_IN_ERROR;
        err = _send_ack(handle, ctx->receive_sender_address);
    }
    else
    {
        // Repeat has correct parity - process it
        ARTIE_CAN_LOG(handle->context, "BWACP: Repeat frame has correct parity; processing\n");

        if (!_receive_fits(ctx, frame->dlc))
        {
            _abort_receive_no_space(handle);
            return ARTIE_CAN_ERR_NO_SPACE;
        }

        memcpy(&ctx->receive_buffer[ctx->receive_address + ctx->receive_bytes_written], frame->data, frame->dlc);
        ctx->receive_bytes_written += frame->dlc;

        // Toggle expected parity for next frame
        ctx->receive_expected_parity = !ctx->receive_expected_parity;
        ctx->receive_accepted_any_frame = true;

        // Send ACK and return to RECEIVING state
        err = _send_ack(handle, ctx->receive_sender_address);
        ctx->state = BWACP_STATE_RECEIVING;
        ctx->transfer_invalidated = false;
        ARTIE_CAN_LOG(handle->context, "BWACP: Repeat frame processed successfully; back to RECEIVING\n");
    }

    return err;
}

/**
 * @brief Handle DATA frame when in RECEIVING state.
 */
static artie_can_error_t _handle_data_receiving(artie_can_backend_t *handle, artie_can_frame_t *frame)
{
    bwacp_context_t *ctx = &handle->context->bwacp_context;
    artie_can_error_t err = ARTIE_CAN_ERR_NONE;

    // Extract parity and repeat flag from frame
    bool frame_parity = (frame->id & BWACP_FRAME_ID_PARITY_MASK) != 0;
    bool is_repeat = (frame->id & BWACP_FRAME_ID_ACK_REPEAT_MASK) != 0;
    bool parity_correct = (frame_parity == ctx->receive_expected_parity);

    if (!parity_correct && is_repeat && ctx->receive_accepted_any_frame)
    {
        // Parity is binary, so a repeat whose parity differs from the one we expect next is exactly
        // the frame we just accepted. On a multicast transfer this is the normal case: the sender
        // repeats because some *other* node missed the frame, so every node that did receive it sees
        // a duplicate. Re-ACK it without writing or toggling parity - NACKing it here would tell the
        // sender to repeat again, and the two sides would ping-pong out of sync.
        ARTIE_CAN_LOG(handle->context, "BWACP: Duplicate repeat of last accepted DATA frame; re-ACKing without writing\n");
        return _send_ack(handle, ctx->receive_sender_address);
    }

    if (!parity_correct)
    {
        // Parity mismatch on a fresh frame - genuine desync. Send NACK and enter EXPECT_REPEAT state
        ARTIE_CAN_LOG(handle->context, "BWACP: DATA frame parity mismatch (expected=%d, got=%d); sending NACK and expecting repeat\n", ctx->receive_expected_parity, frame_parity);
        ctx->state = BWACP_STATE_EXPECT_REPEAT;
        err = _send_nack(handle, ctx->receive_sender_address);
    }
    else
    {
        // Parity correct - process the frame normally
        if (!_receive_fits(ctx, frame->dlc))
        {
            _abort_receive_no_space(handle);
            return ARTIE_CAN_ERR_NO_SPACE;
        }

        memcpy(&ctx->receive_buffer[ctx->receive_address + ctx->receive_bytes_written], frame->data, frame->dlc);
        ctx->receive_bytes_written += frame->dlc;

        // Toggle expected parity for next frame
        ctx->receive_expected_parity = !ctx->receive_expected_parity;
        ctx->receive_accepted_any_frame = true;

        // Send ACK
        err = _send_ack(handle, ctx->receive_sender_address);
        ARTIE_CAN_LOG(handle->context, "BWACP: DATA frame received and ACKed (bytes_written=%u)\n", ctx->receive_bytes_written);
    }

    return err;
}

/**
 * @brief Process DATA frame received in ISR (main thread handler).
 */
static artie_can_error_t _process_data_received(artie_can_backend_t *handle)
{
    bwacp_context_t *ctx = &handle->context->bwacp_context;
    artie_can_error_t err = ARTIE_CAN_ERR_NONE;

    // Only process if we're in receiving, expect repeat, or error state
    if ((ctx->state != BWACP_STATE_RECEIVING) && (ctx->state != BWACP_STATE_EXPECT_REPEAT) && (ctx->state != BWACP_STATE_RECEIVE_IN_ERROR))
    {
        atomic_fetch_and(&ctx->isr_flags, ~((uint32_t)BWACP_ISR_FLAG_DATA_RECEIVED));
        return ARTIE_CAN_ERR_NONE;
    }

    // Get the received frame
    artie_can_frame_t *frame = &ctx->received_data_frame;

    // Handle based on current state
    switch (ctx->state)
    {
    case BWACP_STATE_RECEIVE_IN_ERROR:
        err = _handle_data_received_in_error(handle);
        break;

    case BWACP_STATE_EXPECT_REPEAT:
        err = _handle_data_expect_repeat(handle, frame);
        break;

    case BWACP_STATE_RECEIVING:
        err = _handle_data_receiving(handle, frame);
        break;

    default:
        // Should not reach here due to initial check, but handle gracefully
        break;
    }

    // Update timeout counter
    ctx->last_packet_ms = handle->get_ms();

    atomic_fetch_and(&ctx->isr_flags, ~((uint32_t)BWACP_ISR_FLAG_DATA_RECEIVED));
    return err;
}

/**
 * @brief Process COMPLETE frame received in ISR (main thread handler).
 */
static artie_can_error_t _process_complete_received(artie_can_backend_t *handle)
{
    bwacp_context_t *ctx = &handle->context->bwacp_context;
    artie_can_error_t err = ARTIE_CAN_ERR_NONE;

    // Check if transfer was already invalidated due to parity errors
    if (ctx->transfer_invalidated)
    {
        ARTIE_CAN_LOG(handle->context, "BWACP: Transfer was invalidated due to parity errors; sending NACK\n");

        // Reset state for potential retransmission. The state must go back to RECEIVING: we are
        // almost certainly in RECEIVE_IN_ERROR here, and leaving it there means the sender's restart
        // is ACKed but discarded frame by frame, which loops forever.
        ctx->receive_bytes_written = 0;
        ctx->receive_expected_parity = false;
        ctx->receive_accepted_any_frame = false;
        ctx->transfer_invalidated = false;
        ctx->state = BWACP_STATE_RECEIVING;
        err = _send_nack(handle, ctx->receive_sender_address);
    }
    else if ((ctx->receive_buffer != NULL) && (ctx->receive_bytes_written > 0))
    {
        // Verify CRC
        uint32_t calculated_crc = _crc24_openpgp(&ctx->receive_buffer[ctx->receive_address], ctx->receive_bytes_written);
        if (calculated_crc != ctx->receive_crc24)
        {
            ARTIE_CAN_LOG(handle->context, "BWACP: CRC mismatch (expected=0x%06X, got=0x%06X); sending NACK\n", ctx->receive_crc24, calculated_crc);

            // Reset state for retransmission
            ctx->receive_bytes_written = 0;
            ctx->receive_expected_parity = false;
            ctx->receive_accepted_any_frame = false;
            ctx->state = BWACP_STATE_RECEIVING;
            err = _send_nack(handle, ctx->receive_sender_address);
        }
        else
        {
            ARTIE_CAN_LOG(handle->context, "BWACP: Transfer complete and verified; sending ACK and setting state to IDLE\n");

            // Save this transfer info for cooldown period
            ctx->last_completed_sender_address = ctx->receive_sender_address;
            ctx->last_completed_receive_address = ctx->receive_address;
            ctx->last_completed_timestamp_ms = handle->get_ms();

            // Return to IDLE
            ctx->sending_node_address = 0xFF;
            ctx->receive_accepted_any_frame = false;
            ctx->state = BWACP_STATE_IDLE;

            // Send ACK
            err = _send_ack(handle, ctx->receive_sender_address);
        }
    }
    else
    {
        ARTIE_CAN_LOG(handle->context, "BWACP: COMPLETE received but no data was received; sending NACK\n");
        ctx->receive_expected_parity = false;
        ctx->receive_accepted_any_frame = false;
        ctx->state = BWACP_STATE_RECEIVING;
        err = _send_nack(handle, ctx->receive_sender_address);
    }

    atomic_fetch_and(&ctx->isr_flags, ~((uint32_t)BWACP_ISR_FLAG_COMPLETE_RECEIVED));
    return err;
}

static artie_can_error_t _check_timeout_receiving(artie_can_backend_t *handle)
{
    bwacp_context_t *ctx = &handle->context->bwacp_context;
    uint64_t elapsed = handle->get_ms() - ctx->last_packet_ms;
    if (elapsed >= ARTIE_CAN_BWACP_TIMEOUT_MS)
    {
        ARTIE_CAN_LOG(handle->context, "BWACP: Transfer timeout; setting state to IDLE\n");
        ctx->sending_node_address = 0xFF;
        ctx->state = BWACP_STATE_IDLE;
        return ARTIE_CAN_ERR_TIMEOUT;
    }
    return ARTIE_CAN_ERR_NONE;
}

/**
 * @brief Handle SENDING_READY state - accumulate ACKs after READY frame
 * Spec: DATA frames will be sent after a 1 second cooldown after the last ACK
 */
static artie_can_error_t _handle_sending_ready(artie_can_backend_t *handle)
{
    bwacp_context_t *ctx = &handle->context->bwacp_context;
    uint64_t elapsed = handle->get_ms() - ctx->last_packet_ms;

    // Wait for 1 second to accumulate ACKs
    if (elapsed >= 1000)
    {
        // Cooldown period expired, start sending DATA
        if (ctx->received_ack_count > 0)
        {
            ctx->expected_ack_count = ctx->received_ack_count;
            ctx->active_nodes_bitmap = ctx->ack_received_bitmap; // Save which nodes responded to READY
            ARTIE_CAN_LOG(handle->context, "BWACP: ACK accumulation complete (%u nodes); starting DATA transfer\n", ctx->expected_ack_count);
            ctx->state = BWACP_STATE_SENDING_DATA;
        }
        else
        {
            // No ACKs received - abort transfer
            ARTIE_CAN_LOG(handle->context, "BWACP: No ACKs received after READY; aborting transfer\n");
            ctx->state = BWACP_STATE_IDLE;
            return ARTIE_CAN_ERR_NO_RESPONSE;
        }
    }

    return ARTIE_CAN_ERR_NONE;
}

/**
 * @brief Handle SENDING_DATA state - send DATA frame and transition to waiting for ACKs
 */
static artie_can_error_t _handle_sending_data(artie_can_backend_t *handle)
{
    bwacp_context_t *ctx = &handle->context->bwacp_context;
    artie_can_error_t err;

    // Check if we need to repeat the last DATA frame
    if (ctx->need_repeat_data_frame && ctx->have_sent_data_frame)
    {
        ARTIE_CAN_LOG(handle->context, "BWACP: Repeating last DATA frame\n");
        ctx->need_repeat_data_frame = false;

        // A repeat is a fresh round of ACKs: nodes that ACKed the original still have their bit set
        // in ack_received_bitmap, which would cause their ACK for the repeat to be deduplicated away
        // (and their stale ACK to be counted towards the repeat's quorum).
        atomic_store(&ctx->received_ack_count, 0);
        atomic_store(&ctx->received_nack_count, 0);
        ctx->ack_received_bitmap = 0;
        ctx->last_packet_ms = handle->get_ms();

        // Rebuild the previous frame from last_sent_*; the send cursor and parity stay where they
        // are so that the next fresh frame carries on from the correct place.
        err = _send_data(handle, ctx->last_sent_offset, ctx->last_sent_parity, true);
        if (err != ARTIE_CAN_ERR_NONE)
        {
            return err;
        }
    }
    else
    {
        ctx->need_repeat_data_frame = false;

        // Check if all data has been sent
        if (ctx->send_payload_offset >= ctx->send_payload_size)
        {
            // All data sent, send COMPLETE frame
            ARTIE_CAN_LOG(handle->context, "BWACP: All DATA sent; sending COMPLETE frame\n");
            atomic_store(&ctx->received_ack_count, 0);
            atomic_store(&ctx->received_nack_count, 0);
            ctx->ack_received_bitmap = 0;
            ctx->last_packet_ms = handle->get_ms();
            err = _send_complete(handle);
            ctx->state = BWACP_STATE_SENDING_COMPLETE;
            return err;
        }

        // Get ready for ACKs
        atomic_store(&ctx->received_ack_count, 0);
        atomic_store(&ctx->received_nack_count, 0);
        ctx->ack_received_bitmap = 0; // Clear bitmap for new DATA frame
        ctx->last_packet_ms = handle->get_ms();

        // Remember what we are about to send so that a later repeat can rebuild it exactly
        ctx->last_sent_offset = ctx->send_payload_offset;
        ctx->last_sent_parity = ctx->send_parity;
        ctx->have_sent_data_frame = true;

        // Send next DATA frame
        err = _send_data(handle, ctx->send_payload_offset, ctx->send_parity, false);
        if (err != ARTIE_CAN_ERR_NONE)
        {
            return err;
        }

        // Update offset and toggle parity
        uint32_t bytes_to_send = (ctx->send_payload_size - ctx->send_payload_offset > 8) ? 8 : (ctx->send_payload_size - ctx->send_payload_offset);
        ctx->send_payload_offset += bytes_to_send;
        ctx->send_parity = !ctx->send_parity;
    }

    // Transition to waiting for ACKs
    ctx->state = BWACP_STATE_WAITING_ACK_DATA;

    return ARTIE_CAN_ERR_NONE;
}

/**
 * @brief Handle WAITING_ACK_DATA state - wait for ACKs/NACKs after DATA frame
 * Spec: Each DATA frame is sent as soon as all ACKs are accounted for. After 5 seconds,
 * if not all ACKs/NACKs are accounted for, the transmission is aborted.
 */
static artie_can_error_t _handle_waiting_ack_data(artie_can_backend_t *handle)
{
    bwacp_context_t *ctx = &handle->context->bwacp_context;
    uint64_t elapsed = handle->get_ms() - ctx->last_packet_ms;

    // A NACK from any node means this frame has to be repeated, regardless of how many nodes ACKed
    bool nacked = (ctx->received_nack_count > 0);
    ctx->need_repeat_data_frame = nacked;

    if ((ctx->received_ack_count + ctx->received_nack_count) >= ctx->expected_ack_count)
    {
        if (nacked)
        {
            // A NACK-driven repeat has to count against the repeat budget too, otherwise a receiver
            // that keeps NACKing the same frame keeps the sender in an unbounded repeat loop.
            if (ctx->current_frame_repeat_count >= ARTIE_CAN_BWACP_MAX_REPEATS)
            {
                ARTIE_CAN_LOG(handle->context, "BWACP: DATA frame at offset %u NACKed %u times; aborting transfer\n", ctx->last_sent_offset, ctx->current_frame_repeat_count);
                ctx->need_repeat_data_frame = false;
                ctx->state = BWACP_STATE_IDLE;
                return ARTIE_CAN_ERR_SEND_FAIL;
            }

            ctx->current_frame_repeat_count++;
            ARTIE_CAN_LOG(handle->context, "BWACP: NACK received; will repeat DATA frame (%u/%u)\n", ctx->current_frame_repeat_count, ARTIE_CAN_BWACP_MAX_REPEATS);
        }
        else
        {
            // All ACKs received - move on to the next frame
            ARTIE_CAN_LOG(handle->context, "BWACP: All ACKs received; sending next DATA frame\n");
            ctx->current_frame_repeat_count = 0; // Reset repeat count for next frame
        }

        ctx->state = BWACP_STATE_SENDING_DATA;
    }
    else if (elapsed >= ARTIE_CAN_BWACP_ACK_TIMEOUT_MS)
    {
        // Timeout - try repeating or blacklist non-responsive nodes
        if (ctx->current_frame_repeat_count >= ARTIE_CAN_BWACP_MAX_REPEATS)
        {
            // Max repeats exhausted - blacklist non-responsive nodes and continue
            // Identify non-responsive nodes: in active_nodes_bitmap but NOT in ack_received_bitmap
            uint64_t non_responsive_nodes = ctx->active_nodes_bitmap & ~ctx->ack_received_bitmap;

            if (non_responsive_nodes != 0)
            {
                // Add non-responsive nodes to blacklist
                ctx->blacklisted_nodes_bitmap |= non_responsive_nodes;

                // Remove blacklisted nodes from active nodes
                ctx->active_nodes_bitmap &= ~non_responsive_nodes;

                // Count remaining active nodes
                uint32_t new_expected_ack_count = 0;
                for (int i = 0; i < 64; i++)
                {
                    if ((ctx->active_nodes_bitmap & (1ULL << i)) != 0)
                    {
                        new_expected_ack_count++;
                    }
                }

                ARTIE_CAN_LOG(handle->context, "BWACP: ACK timeout and repeats exhausted (%u/%u ACKs); blacklisting %u non-responsive nodes\n", ctx->received_ack_count, ctx->expected_ack_count, (ctx->expected_ack_count - new_expected_ack_count));

                ctx->expected_ack_count = new_expected_ack_count;

                // Check if any nodes are still active
                if (ctx->expected_ack_count == 0)
                {
                    ARTIE_CAN_LOG(handle->context, "BWACP: All nodes blacklisted; aborting transmission\n");
                    ctx->state = BWACP_STATE_IDLE;
                    return ARTIE_CAN_ERR_TIMEOUT;
                }

                ARTIE_CAN_LOG(handle->context, "BWACP: Continuing transfer with %u remaining nodes\n", ctx->expected_ack_count);
            }

            // Reset repeat count and continue with next DATA frame
            ctx->need_repeat_data_frame = false;
            ctx->current_frame_repeat_count = 0;
            ctx->state = BWACP_STATE_SENDING_DATA;
        }
        else
        {
            ARTIE_CAN_LOG(handle->context, "BWACP: ACK timeout (%u/%u ACKs); repeating DATA frame\n", ctx->received_ack_count, ctx->expected_ack_count);
            ctx->need_repeat_data_frame = true;
            ctx->current_frame_repeat_count++;
            ctx->state = BWACP_STATE_SENDING_DATA;
        }
    }

    return ARTIE_CAN_ERR_NONE;
}

/**
 * @brief Handle SENDING_COMPLETE state - wait for ACKs/NACKs after COMPLETE frame
 * Spec: Once all ACKs are accounted for (or a 5s timeout has completed), the sender considers the transfer complete.
 */
static artie_can_error_t _handle_sending_complete(artie_can_backend_t *handle)
{
    bwacp_context_t *ctx = &handle->context->bwacp_context;
    uint64_t elapsed = handle->get_ms() - ctx->last_packet_ms;

    // Check if we received any NACKs
    if (ctx->received_nack_count > 0)
    {
        // NACK received - restart transfer, but only a bounded number of times. Without a bound, a
        // receiver that cannot be resynchronized keeps NACKing every COMPLETE and the sender streams
        // the whole payload again indefinitely.
        if (ctx->transfer_restart_count >= ARTIE_CAN_BWACP_MAX_TRANSFER_RESTARTS)
        {
            ARTIE_CAN_LOG(handle->context, "BWACP: NACK received after COMPLETE but restart limit (%u) reached; aborting transfer\n", ARTIE_CAN_BWACP_MAX_TRANSFER_RESTARTS);
            ctx->state = BWACP_STATE_IDLE;
            return ARTIE_CAN_ERR_SEND_FAIL;
        }

        ctx->transfer_restart_count++;
        ARTIE_CAN_LOG(handle->context, "BWACP: NACK received after COMPLETE; restarting transfer (%u/%u)\n", ctx->transfer_restart_count, ARTIE_CAN_BWACP_MAX_TRANSFER_RESTARTS);
        ctx->send_payload_offset = 0;
        ctx->send_parity = false;
        ctx->have_sent_data_frame = false;
        atomic_store(&ctx->received_ack_count, 0);
        atomic_store(&ctx->received_nack_count, 0);
        ctx->ack_received_bitmap = 0;
        ctx->need_repeat_data_frame = false;
        ctx->current_frame_repeat_count = 0;
        ctx->state = BWACP_STATE_SENDING_DATA;
    }
    else if (ctx->received_ack_count >= ctx->expected_ack_count)
    {
        // All ACKs received - transfer complete
        ARTIE_CAN_LOG(handle->context, "BWACP: All ACKs received after COMPLETE; transfer successful\n");
        ctx->state = BWACP_STATE_IDLE;
    }
    else if (elapsed >= ARTIE_CAN_BWACP_TIMEOUT_MS)
    {
        // Timeout - consider transfer complete anyway
        ARTIE_CAN_LOG(handle->context, "BWACP: ACK timeout after COMPLETE (%u/%u ACKs); transfer complete\n", ctx->received_ack_count, ctx->expected_ack_count);
        ctx->state = BWACP_STATE_IDLE;
        return ARTIE_CAN_ERR_TIMEOUT;
    }

    return ARTIE_CAN_ERR_NONE;
}

artie_can_error_t artie_can_init_context_bwacp(artie_can_context_t *context, uint8_t node_address, uint8_t node_class)
{
    if (context == NULL)
    {
        return ARTIE_CAN_ERR_INVALID_ARG;
    }
    if (node_address >= ARTIE_CAN_BWACP_MULTICAST_ADDRESS)
    {
        return ARTIE_CAN_ERR_INVALID_ARG;
    }

    // Initialize BWACP context
    memset(&context->bwacp_context, 0, sizeof(bwacp_context_t));
    context->bwacp_context.node_address = node_address;
    context->bwacp_context.node_class = node_class;
    context->bwacp_context.state = BWACP_STATE_IDLE;
    context->bwacp_context.sending_node_address = 0xFF;

    // Enable BWACP protocol
    context->protocol_flags |= ARTIE_CAN_PROTOCOL_FLAG_BWACP;
    context->node_address = node_address;

    return ARTIE_CAN_ERR_NONE;
}

artie_can_error_t artie_can_bwacp_set_receive_buffer(artie_can_context_t *context, uint8_t *buffer, uint32_t buffer_size)
{
    if (context == NULL || buffer == NULL)
    {
        return ARTIE_CAN_ERR_INVALID_ARG;
    }

    context->bwacp_context.receive_buffer = buffer;
    context->bwacp_context.receive_buffer_size = buffer_size;

    return ARTIE_CAN_ERR_NONE;
}

artie_can_error_t artie_can_bwacp_send(artie_can_backend_t *handle, const uint8_t *payload, uint32_t payload_size, uint32_t address, uint8_t target_address, uint8_t target_class, artie_can_frame_priority_bwacp_t priority)
{
    if (handle == NULL || payload == NULL)
    {
        return ARTIE_CAN_ERR_INVALID_ARG;
    }

    bwacp_context_t *ctx = &handle->context->bwacp_context;

    // Check if we're already busy
    if (ctx->state != BWACP_STATE_IDLE)
    {
        return ARTIE_CAN_ERR_SEND_BUSY;
    }

    // Initialize send state
    ARTIE_CAN_LOG(handle->context, "BWACP: Initiating send (addr=0x%08X, size=%u); sending READY and waiting for ACKs\n", address, payload_size);
    ctx->send_payload = payload;
    ctx->send_payload_size = payload_size;
    ctx->send_payload_offset = 0;
    ctx->send_address = address;
    ctx->send_target_address = target_address;
    ctx->send_target_class = target_class;
    ctx->send_parity = false;
    ctx->last_sent_offset = 0;
    ctx->last_sent_parity = false;
    ctx->have_sent_data_frame = false;
    ctx->transfer_restart_count = 0;
    ctx->expected_ack_count = 0;
    ctx->received_ack_count = 0;
    ctx->received_nack_count = 0;
    ctx->need_repeat_data_frame = false;
    ctx->current_frame_repeat_count = 0;
    ctx->ack_received_bitmap = 0;
    ctx->active_nodes_bitmap = 0;
    ctx->blacklisted_nodes_bitmap = 0; // Clear blacklist for new transfer
    ctx->last_packet_ms = handle->get_ms();

    // Send READY frame
    artie_can_error_t err = _send_ready(handle, payload, payload_size, address, target_address, target_class, priority);
    if (err != ARTIE_CAN_ERR_NONE)
    {
        ctx->state = BWACP_STATE_IDLE;
        return err;
    }

    // Transition to SENDING_READY state to wait for ACKs
    ctx->state = BWACP_STATE_SENDING_READY;

    return ARTIE_CAN_ERR_NONE;
}

bool artie_can_bwacp_is_busy(artie_can_backend_t *handle)
{
    if ((handle == NULL) || (handle->context == NULL))
    {
        return false;
    }

    bwacp_context_t *ctx = &handle->context->bwacp_context;
    return (ctx->state != BWACP_STATE_IDLE);
}

void bwacp_receive_in_isr(artie_can_context_t *context, const artie_can_frame_t *frame)
{
    if ((context->protocol_flags & ARTIE_CAN_PROTOCOL_FLAG_BWACP) == 0)
    {
        return;
    }

    // Extract frame type
    uint8_t frame_type = (uint8_t)((frame->id & ARTIE_CAN_FRAME_ID_FRAME_TYPE_MASK) >> ARTIE_CAN_FRAME_ID_FRAME_TYPE_LOCATION);

    // Dispatch based on frame type
    switch (frame_type)
    {
        case ARTIE_CAN_FRAME_TYPE_BWACP_READY:
            _process_ready_frame_from_isr(context, frame);
            break;

        case ARTIE_CAN_FRAME_TYPE_BWACP_DATA:
            _process_data_frame_from_isr(context, frame);
            break;

        case ARTIE_CAN_FRAME_TYPE_BWACP_COMPLETE:
            _process_complete_frame_from_isr(context, frame);
            break;

        case ARTIE_CAN_FRAME_TYPE_BWACP_ACK_NACK:
            _process_ack_nack_frame_from_isr(context, frame);
            break;

        default:
            break;
    }
}

artie_can_error_t bwacp_tick(artie_can_backend_t *handle)
{
    if ((handle == NULL) || (handle->context == NULL))
    {
        return ARTIE_CAN_ERR_INVALID_ARG;
    }

    bwacp_context_t *ctx = &handle->context->bwacp_context;
    artie_can_error_t err = ARTIE_CAN_ERR_NONE;

    // Process ISR flags
    if ((ctx->isr_flags & BWACP_ISR_FLAG_READY_RECEIVED) != 0)
    {
        err |= _process_ready_received(handle);
    }

    if ((ctx->isr_flags & BWACP_ISR_FLAG_DATA_RECEIVED) != 0)
    {
        err |= _process_data_received(handle);
    }

    if ((ctx->isr_flags & BWACP_ISR_FLAG_COMPLETE_RECEIVED) != 0)
    {
        err |= _process_complete_received(handle);
    }

    // State machine
    switch (ctx->state)
    {
        case BWACP_STATE_SENDING_READY:
            err |= _handle_sending_ready(handle);
            break;
        case BWACP_STATE_SENDING_DATA:
            err |= _handle_sending_data(handle);
            break;
        case BWACP_STATE_WAITING_ACK_DATA:
            err |= _handle_waiting_ack_data(handle);
            break;
        case BWACP_STATE_SENDING_COMPLETE:
            err |= _handle_sending_complete(handle);
            break;
        case BWACP_STATE_RECEIVE_IN_ERROR: // fall-through
        case BWACP_STATE_EXPECT_REPEAT: // fall-through
        case BWACP_STATE_RECEIVING:
            err |= _check_timeout_receiving(handle);
            break;
        case BWACP_STATE_IDLE:
            break;
        default:
            break;
    }

    return err;
}
