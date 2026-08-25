/**
 * @file bwacp_context.h
 * @brief Definitions for BWACP context and related functions in the Artie CAN library.
 *
 */

#pragma once

#include <stdbool.h>
#include <stdint.h>
#include "frame.h"
#include "translationlayer.h"

/**
 * Default size of the buffer a receiver hands to artie_can_bwacp_set_receive_buffer().
 *
 * BWACP has no maximum transfer size: nothing on the wire carries a length, a transfer runs until
 * the COMPLETE frame, and the offset and byte counters are 32-bit. What a receiver can actually
 * take is the buffer it supplies, so this is only the size the bindings pick when the caller does
 * not choose one - a receiver that needs more should just allocate more.
 */
#define ARTIE_CAN_BWACP_DEFAULT_BUFFER_SIZE (65536U)

/** Maximum number of times a DATA frame can be repeated */
#define ARTIE_CAN_BWACP_MAX_REPEATS (5U)

/** Maximum number of times a whole transfer can be restarted after a receiver NACKs the COMPLETE frame */
#define ARTIE_CAN_BWACP_MAX_TRANSFER_RESTARTS (3U)

/**
 * @brief States that the BWACP state machine can be in for a given node.
 *
 */
typedef enum {
    BWACP_STATE_IDLE,              ///< The node is idle and not currently processing any block write.
    BWACP_STATE_SENDING_READY,     ///< The node has sent a READY frame and is waiting for ACKs.
    BWACP_STATE_SENDING_DATA,      ///< The node is sending DATA frames.
    BWACP_STATE_WAITING_ACK_DATA,  ///< The node has sent a DATA frame and is waiting for ACKs.
    BWACP_STATE_SENDING_COMPLETE,  ///< The node has sent a COMPLETE frame and is waiting for ACKs.
    BWACP_STATE_RECEIVING,         ///< The node is receiving a block write.
    BWACP_STATE_EXPECT_REPEAT,     ///< The node has sent a NACK and is expecting a repeat of the last DATA frame.
    BWACP_STATE_RECEIVE_IN_ERROR,  ///< The node is receiving a block write but has detected a parity error and is waiting for the transfer to end to request retransmission.
} bwacp_state_t;

/**
 * @brief ISR flags for BWACP protocol.
 */
typedef enum {
    BWACP_ISR_FLAG_NONE = 0,                 ///< No special conditions for this ISR call
    BWACP_ISR_FLAG_READY_RECEIVED = 1 << 0,  ///< A READY frame was received in the ISR
    BWACP_ISR_FLAG_DATA_RECEIVED = 1 << 1,   ///< A DATA frame was received in the ISR
    BWACP_ISR_FLAG_COMPLETE_RECEIVED = 1 << 2, ///< A COMPLETE frame was received in the ISR
} bwacp_isr_flags_t;

/**
 * @brief Context for BWACP protocol handling within the Artie CAN library.
 *
 */
typedef struct {
    // Written to by main thread
    uint8_t node_address;                   ///< The BWACP address of this node on the CAN bus
    uint8_t node_class;                     ///< The class bitmask of this node (bit 0=SBC, bit 1=MCU, bit 2=Sensor, bit 3=Motor, bits 4-5=Reserved)
    bwacp_state_t state;                    ///< The current state of the BWACP protocol for this node
    uint64_t last_packet_ms;                ///< The time in milliseconds when the latest packet has been received or sent

    // Sending state
    const uint8_t *send_payload;            ///< Pointer to the payload being sent (owned by caller)
    uint32_t send_payload_size;             ///< Size of the payload being sent
    uint32_t send_payload_offset;           ///< Current offset in the send payload
    uint32_t send_address;                  ///< Buffer offset where the receiving node(s) should write the data
    uint8_t send_target_address;            ///< Target node address (or 0x3F for multicast)
    uint8_t send_target_class;              ///< Target class bitmask (for multicast)
    bool send_parity;                       ///< Parity bit to use for the next fresh DATA frame
    uint32_t last_sent_offset;              ///< Payload offset of the most recently transmitted DATA frame (used to build repeats without disturbing the send cursor)
    bool last_sent_parity;                  ///< Parity bit of the most recently transmitted DATA frame
    bool have_sent_data_frame;              ///< Whether at least one DATA frame has been transmitted for the current transfer
    uint32_t transfer_restart_count;        ///< Number of times the current transfer has been restarted from offset 0
    uint32_t send_crc24;                    ///< CRC24 over the payload
    uint32_t expected_ack_count;            ///< Number of ACKs expected after READY, DATA, or COMPLETE frames
    uint32_t received_ack_count;            ///< Number of ACKs received so far
    uint32_t received_nack_count;           ///< Number of NACKs received so far
    bool need_repeat_data_frame;            ///< Whether the last DATA frame needs to be repeated due to NACK
    uint32_t current_frame_repeat_count;    ///< Number of times the current DATA frame has been repeated
    uint64_t ack_received_bitmap;           ///< Bitmap of nodes that have sent ACK for the current frame (bit N = node address N)
    uint64_t active_nodes_bitmap;           ///< Bitmap of nodes actively participating in transfer (responded to READY and not blacklisted)
    uint64_t blacklisted_nodes_bitmap;      ///< Bitmap of nodes blacklisted for current transfer due to non-responsiveness

    // Receiving state
    uint8_t *receive_buffer;                ///< Buffer for receiving data (owned by caller, must be provided before receiving)
    uint32_t receive_buffer_size;           ///< Size of the receive buffer
    uint32_t receive_bytes_written;         ///< Number of bytes written to the receive buffer so far
    uint32_t receive_address;               ///< Buffer offset where received data should be written
    uint8_t receive_sender_address;         ///< Address of the sender
    bool receive_expected_parity;           ///< Expected parity bit for next DATA frame
    bool receive_accepted_any_frame;        ///< Whether at least one DATA frame has been accepted for the current transfer (a repeat can only be a duplicate if we have already accepted something)
    uint32_t receive_crc24;                 ///< Expected CRC24 for the received data
    bool receive_ready_interrupt;           ///< Whether the READY frame had the interrupt bit set
    uint8_t sending_node_address;           ///< The address of the node we are receiving from
    bool transfer_invalidated;              ///< Whether the current transfer has been invalidated due to a parity error (used to determine whether to request retransmission at the end)

    // Last completed transfer tracking (to prevent duplicate reception of same transfer during REPEAT cooldown)
    uint8_t last_completed_sender_address;  ///< Sender address of last completed transfer
    uint32_t last_completed_receive_address; ///< Receive address of last completed transfer
    uint64_t last_completed_timestamp_ms;   ///< Timestamp when last transfer completed

    // Written to by ISR (each ISR type has its own dedicated frame)
    artie_can_frame_t received_ready_frame;     ///< Most recently received READY frame (for processing in main thread)
    artie_can_frame_t received_data_frame;      ///< Most recently received DATA frame (for processing in main thread)
    artie_can_frame_t received_complete_frame;  ///< Most recently received COMPLETE frame (for processing in main thread)
    artie_can_frame_t received_ack_nack_frame;  ///< Most recently received ACK/NACK frame (for processing in main thread)
    atomic_uint32_t isr_flags;              ///< Flags to indicate special conditions found during ISR; cleared by main thread (atomic operations required)
} bwacp_context_t;
