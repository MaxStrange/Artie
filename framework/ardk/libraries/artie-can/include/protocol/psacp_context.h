/**
 * @file psacp_context.h
 * @brief Definitions for PSACP context and related functions in the Artie CAN library.
 *
 */

#pragma once

#include <stdbool.h>
#include <stdint.h>
#include "frame.h"
#include "translationlayer.h"

/** Maximum number of topics a single node can subscribe to simultaneously */
#define ARTIE_CAN_PSACP_MAX_SUBSCRIPTIONS 32U

/**
 * Number of multi-frame messages a node can be reassembling at once.
 *
 * Each slot holds a whole message (see ARTIE_CAN_PSACP_MAX_MESSAGE_SIZE in psacp.h), so this
 * directly sets how much RAM PSACP adds to every node's context - roughly 4.4 KB at the default of
 * 8. Slots are claimed per (sender, topic) pair, so what this needs to cover is how many
 * publishers can have a message in flight simultaneously across all subscribed topics, not how
 * many topics there are. Override at compile time on memory-constrained MCUs.
 */
#ifndef ARTIE_CAN_PSACP_REASSEMBLY_SLOTS
#define ARTIE_CAN_PSACP_REASSEMBLY_SLOTS 8U
#endif

/**
 * Size of a reassembly slot's payload buffer.
 *
 * Kept in step with ARTIE_CAN_PSACP_MAX_MESSAGE_SIZE in psacp.h, which cannot be used here: that
 * header includes context.h, which includes this one, so the constant is not yet visible. psacp.c
 * asserts the two agree.
 */
#define ARTIE_CAN_PSACP_SLOT_BUFFER_SIZE 527U

/**
 * @brief States a reassembly slot can be in.
 */
typedef enum {
    PSACP_SLOT_FREE = 0,        ///< Not in use; available to claim.
    PSACP_SLOT_RECEIVING,       ///< A PUB_START has arrived and more fragments are expected.
    PSACP_SLOT_COMPLETE,        ///< A whole message is buffered, waiting for the main thread to take it.
} psacp_slot_state_t;

/**
 * @brief One in-progress or completed inbound message.
 *
 * Slots are keyed on (source_address, topic) rather than topic alone. CAN arbitration interleaves
 * concurrent publishers' frames, so two nodes publishing to one topic at the same time would have
 * their fragments spliced together if only the topic were matched on.
 */
typedef struct {
    psacp_slot_state_t state;       ///< What this slot is currently holding
    uint8_t source_address;         ///< Address of the publishing node (half of the slot's key)
    uint8_t topic;                  ///< Topic being published to (the other half of the key)
    uint8_t promised_more_count;    ///< PUB_MORE frames the PUB_START said would follow
    uint8_t received_more_count;    ///< PUB_MORE frames accepted so far
    uint8_t next_expected_index;    ///< Fragment index the next PUB_MORE must carry
    uint16_t nbytes;                ///< Bytes written into data so far
    /**
     * When this slot was last seen making progress, used to age it out.
     *
     * Written by psacp_tick(), not by the ISR that accepts the fragments: the receive path is
     * handed only a context, while the clock lives on the backend handle. The tick infers activity
     * by watching nbytes against last_seen_nbytes instead, which is accurate to one tick - far
     * finer than the timeout this feeds.
     */
    uint64_t last_activity_ms;
    uint16_t last_seen_nbytes;      ///< nbytes as of the last tick, for the activity check above
    uint8_t data[ARTIE_CAN_PSACP_SLOT_BUFFER_SIZE]; ///< The message being reassembled
} psacp_reassembly_slot_t;

/**
 * @brief State of a multi-frame publish that is still emitting frames.
 */
typedef struct {
    bool active;                    ///< Whether a publish is in flight
    uint8_t topic;                  ///< Topic being published to
    uint8_t priority;               ///< User-assigned priority for every frame of this message
    uint8_t more_count;             ///< Total PUB_MORE frames this message needs
    uint8_t more_sent;              ///< PUB_MORE frames emitted so far
    bool start_sent;                ///< Whether the PUB_START frame has gone out
    bool deliver_locally;           ///< Whether this node subscribes to the topic and must self-deliver
    uint16_t nbytes;                ///< Length of the payload
    uint8_t data[ARTIE_CAN_PSACP_SLOT_BUFFER_SIZE]; ///< Copy of the payload being sent
} psacp_send_state_t;

/**
 * @brief Context for PSACP protocol handling within the Artie CAN library.
 *
 * PSACP is a fire-and-forget pub/sub protocol with no ACK or retransmission. Messages that fit in
 * a single frame pass straight through; longer ones are fragmented on send and reassembled on
 * receive, which is what the slots below are for.
 */
typedef struct {
    uint8_t node_address;                                           ///< The address of this node on the CAN bus
    uint8_t subscribed_topics[ARTIE_CAN_PSACP_MAX_SUBSCRIPTIONS];   ///< Array of topics this node has subscribed to
    uint8_t subscribed_topic_count;                                 ///< Number of active subscriptions

    // Written to by main thread
    psacp_send_state_t send;                ///< The multi-frame publish currently being emitted, if any
    uint32_t dropped_message_count;         ///< Inbound messages discarded rather than delivered incomplete

    // Written to by ISR (reassembly happens there; the main thread drains completed slots by
    // scanning them - there is deliberately no "something is ready" flag, because a flag the
    // reader had to clear could be cleared over a completion that landed mid-scan, losing the
    // message. The scan is a handful of comparisons.)
    psacp_reassembly_slot_t slots[ARTIE_CAN_PSACP_REASSEMBLY_SLOTS]; ///< In-progress and completed inbound messages
} psacp_context_t;
