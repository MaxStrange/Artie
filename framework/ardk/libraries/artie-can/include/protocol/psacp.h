/**
 * @file psacp.h
 * @brief Header file for Artie CAN PSACP (Pub/Sub Artie CAN Protocol) implementation.
 *
 */

#pragma once

#include <stdbool.h>
#include <stdint.h>
#include "backend.h"
#include "context.h"
#include "err.h"
#include "frame.h"

/** The PSACP (high priority) protocol ID - 100 in binary */
#define ARTIE_CAN_PSACP_HIGH_PROTOCOL_ID 0x04U

/** The PSACP (low priority) protocol ID - 110 in binary */
#define ARTIE_CAN_PSACP_LOW_PROTOCOL_ID 0x06U

/** Maximum number of data bytes in a PSACP frame */
#define ARTIE_CAN_PSACP_MAX_DATA_BYTES 8U

/** The PSACP PUB frame type - a complete message of 8 bytes or fewer */
#define ARTIE_CAN_PSACP_FRAME_TYPE_PUB 0x01U

/** The PSACP PUB_START frame type - first fragment of a multi-frame message */
#define ARTIE_CAN_PSACP_FRAME_TYPE_PUB_START 0x02U

/** The PSACP PUB_MORE frame type - continuation of a multi-frame message */
#define ARTIE_CAN_PSACP_FRAME_TYPE_PUB_MORE 0x03U

/** The PSACP PUB_END frame type - final fragment of a multi-frame message */
#define ARTIE_CAN_PSACP_FRAME_TYPE_PUB_END 0x04U

/** Broadcast topic value - send to all subscribers */
#define ARTIE_CAN_PSACP_TOPIC_BROADCAST 0x00U

/** Location of the topic bits in the PSACP frame ID.
 *  Topic is 8 bits wide, occupying bits [13:6] of the 29-bit CAN ID. */
#define PSACP_FRAME_ID_TOPIC_LOCATION 6U

/** Mask for topic bits in the PSACP frame ID */
#define PSACP_FRAME_ID_TOPIC_MASK (0xFFU << PSACP_FRAME_ID_TOPIC_LOCATION)

/** Location of the fragment index bits in the PSACP frame ID.
 *  The index is 6 bits wide, occupying bits [5:0] of the 29-bit CAN ID - the bits that
 *  single-frame PUB, PUB_START and PUB_END leave reserved. Only PUB_MORE carries an index. */
#define PSACP_FRAME_ID_INDEX_LOCATION 0U

/** Mask for the fragment index bits in the PSACP frame ID */
#define PSACP_FRAME_ID_INDEX_MASK (0x3FU << PSACP_FRAME_ID_INDEX_LOCATION)

/**
 * Number of payload bytes a PUB_START frame carries.
 *
 * One of its eight data bytes is spent on the count of PUB_MORE frames that follow, which is what
 * lets a receiver notice that the *last* PUB_MORE went missing: without it, an index-free PUB_END
 * arriving early is indistinguishable from a legitimately shorter message, and the message would
 * be delivered 8 bytes short with PUB_END's payload spliced where the lost frame's belonged.
 */
#define ARTIE_CAN_PSACP_START_PAYLOAD_BYTES 7U

/** Offset of the PUB_MORE-count byte within a PUB_START frame's data field. */
#define ARTIE_CAN_PSACP_START_COUNT_OFFSET 0U

/** Maximum number of PUB_MORE frames in a single message (the 6-bit index space). */
#define ARTIE_CAN_PSACP_MAX_MORE_FRAMES 64U

/**
 * Largest message a single publish can carry: 7 bytes in PUB_START, 8 in each of up to 64
 * PUB_MORE frames, and up to 8 more in PUB_END.
 */
#define ARTIE_CAN_PSACP_MAX_MESSAGE_SIZE \
    ((ARTIE_CAN_PSACP_START_PAYLOAD_BYTES) + \
     ((ARTIE_CAN_PSACP_MAX_MORE_FRAMES) * (ARTIE_CAN_PSACP_MAX_DATA_BYTES)) + \
     (ARTIE_CAN_PSACP_MAX_DATA_BYTES))

/**
 * How long a partially received message may sit idle before its slot is reclaimed.
 *
 * A maximum-size message is ~66 frames, which is around 20 ms of bus time at 500 kbps; this is
 * generous enough to survive arbitration against higher-priority traffic while still bounding how
 * long a slot is held by a transfer whose PUB_END was lost.
 */
#define ARTIE_CAN_PSACP_REASSEMBLY_TIMEOUT_MS 1000U

/**
 * Maximum frames emitted per artie_can_tick() while a multi-frame publish is in flight.
 *
 * Sending all of a message's frames inside artie_can_psacp_publish_message() would block the
 * caller - and, in the Python bindings, the thread that drives every protocol's tick - for the
 * whole transfer. Pacing the burst also gives receivers a chance to drain their controller's RX
 * buffers, which is what fails first when frames arrive back to back.
 */
#define ARTIE_CAN_PSACP_FRAMES_PER_TICK 4U

/**
 * @brief Enumeration for PSACP frame priorities.
 *
 */
typedef enum {
    ARTIE_CAN_FRAME_PRIORITY_PSACP_LOW = 3,        ///< Low priority frame
    ARTIE_CAN_FRAME_PRIORITY_PSACP_MEDIUM_LOW = 2, ///< Medium-low priority frame
    ARTIE_CAN_FRAME_PRIORITY_PSACP_MEDIUM_HIGH = 1,///< Medium-high priority frame
    ARTIE_CAN_FRAME_PRIORITY_PSACP_HIGH = 0,       ///< High priority frame
} artie_can_frame_priority_psacp_t;

/**
 * @brief Structure representing a PSACP frame, as opposed to the more general artie_can_frame_t.
 *
 */
typedef struct {
    bool high_priority;                              ///< true = high priority pub/sub (protocol 0x04), false = low priority (protocol 0x06)
    artie_can_frame_priority_psacp_t priority;       ///< User-assigned priority within the PSACP protocol
    uint8_t source_address;                          ///< Source address of the frame
    uint8_t topic;                                   ///< Topic this message is published to (0x00 = broadcast)
    uint8_t nbytes;                                  ///< Number of data bytes in the message (0-8)
    uint8_t data[ARTIE_CAN_PSACP_MAX_DATA_BYTES];    ///< Data bytes of the message (up to 8 bytes)
} artie_can_frame_psacp_t;

/**
 * @brief A complete PSACP message, which may have arrived across several frames.
 *
 * This is what artie_can_psacp_get_message() hands back, as opposed to artie_can_frame_psacp_t,
 * which is a single frame. A message that fit in one frame is reported here too, so callers that
 * poll do not have to handle single- and multi-frame messages differently.
 */
typedef struct {
    uint8_t source_address;                             ///< Address of the node that published this message
    uint8_t topic;                                      ///< Topic the message was published to
    uint16_t nbytes;                                    ///< Number of valid bytes in data
    uint8_t data[ARTIE_CAN_PSACP_MAX_MESSAGE_SIZE];     ///< The reassembled payload
} artie_can_psacp_message_t;

/**
 * @brief Initialize a PSACP context with the specified node address.
 *
 * @param ctx Pointer to the artie_can_context_t struct to initialize.
 * @param node_address Node address to use for the PSACP context.
 * @return artie_can_error_t Error code indicating the result of the initialization.
 */
artie_can_error_t artie_can_init_context_psacp(artie_can_context_t *ctx, uint8_t node_address);

/**
 * @brief Subscribe this node to a given PSACP topic.
 * When a frame is published to this topic (or to the broadcast topic 0x00), this node will
 * receive it via the rx_callback.
 *
 * @param ctx Pointer to the artie_can_context_t struct.
 * @param topic The topic to subscribe to (must be in range 0x0B - 0xF4).
 * @return artie_can_error_t Error code indicating the result of the operation.
 */
artie_can_error_t artie_can_psacp_subscribe(artie_can_context_t *ctx, uint8_t topic);

/**
 * @brief Unsubscribe this node from a given PSACP topic.
 *
 * @param ctx Pointer to the artie_can_context_t struct.
 * @param topic The topic to unsubscribe from.
 * @return artie_can_error_t Error code indicating the result of the operation.
 *         Returns ARTIE_CAN_ERR_NO_DATA if the node was not subscribed to the topic.
 */
artie_can_error_t artie_can_psacp_unsubscribe(artie_can_context_t *ctx, uint8_t topic);

/**
 * @brief Initialize a raw artie_can_frame_t with the PSACP headers and data from an artie_can_frame_psacp_t.
 *
 * @param out Pointer to the artie_can_frame_t to initialize.
 * @param in Pointer to the artie_can_frame_psacp_t describing the message to send.
 * @return artie_can_error_t Error code indicating the result of the operation.
 */
artie_can_error_t artie_can_psacp_init_frame(artie_can_frame_t *out, const artie_can_frame_psacp_t *in);

/**
 * @brief Parse a received raw artie_can_frame_t into an artie_can_frame_psacp_t.
 *
 * @param in Pointer to the raw artie_can_frame_t to parse.
 * @param out Pointer to the artie_can_frame_psacp_t to populate.
 * @return artie_can_error_t Error code indicating the result of the operation.
 */
artie_can_error_t artie_can_psacp_parse_frame(const artie_can_frame_t *in, artie_can_frame_psacp_t *out);

/**
 * @brief Publish a PSACP frame to the bus. This function is fire-and-forget; there is no ACK.
 * If the publishing node is itself subscribed to the topic (or the topic is broadcast), it will
 * also deliver the message locally via the rx_callback before returning.
 *
 * @param handle Pointer to the artie_can_backend_t struct representing the backend.
 * @param frame Pointer to the raw artie_can_frame_t to publish.
 * @return artie_can_error_t Error code indicating the result of the operation.
 */
artie_can_error_t artie_can_psacp_publish(artie_can_backend_t *handle, const artie_can_frame_t *frame);

/**
 * @brief Publish a message of any supported length to a topic, fragmenting it if needed.
 *
 * Messages of 8 bytes or fewer go out as a single PUB frame, exactly as artie_can_psacp_publish()
 * would send them. Longer ones are split across a PUB_START, up to
 * ARTIE_CAN_PSACP_MAX_MORE_FRAMES PUB_MORE frames, and a PUB_END.
 *
 * This function only *queues* the message: frames are emitted by subsequent artie_can_tick()
 * calls, so keep ticking until artie_can_psacp_is_busy() returns false. Like the rest of PSACP
 * there is no ACK and nothing is retried - a receiver that misses a fragment drops the whole
 * message rather than delivering part of one.
 *
 * @param handle Pointer to the artie_can_backend_t struct representing the backend.
 * @param topic The topic to publish to.
 * @param data The payload. Copied into the context, so the caller may reuse it once this returns.
 * @param nbytes Length of the payload, at most ARTIE_CAN_PSACP_MAX_MESSAGE_SIZE.
 * @param priority Bus arbitration priority within the PSACP protocol.
 * @param high_priority Use the high-priority PSACP protocol ID. Only permitted for payloads that
 * fit in a single frame: high-priority PSACP arbitrates above BWACP, so a multi-frame burst there
 * would stall block transfers such as firmware updates. Rejected with ARTIE_CAN_ERR_INVALID_ARG
 * for longer payloads.
 * @return artie_can_error_t Error code indicating the result of the operation.
 */
artie_can_error_t artie_can_psacp_publish_message(artie_can_backend_t *handle, uint8_t topic, const uint8_t *data, uint16_t nbytes, artie_can_frame_priority_psacp_t priority, bool high_priority);

/**
 * @brief Check whether a multi-frame publish is still emitting frames.
 *
 * @param handle Pointer to the artie_can_backend_t struct representing the backend.
 * @return true if a publish started by artie_can_psacp_publish_message() has frames left to send.
 */
bool artie_can_psacp_is_busy(artie_can_backend_t *handle);

/**
 * @brief Pop the oldest fully reassembled multi-frame message, if there is one.
 *
 * Only messages that spanned more than one frame appear here. A message that fit in a single frame
 * *is* a frame, so it goes to the rx_callback the moment it arrives, exactly as it did before
 * fragmentation existed - it is not repeated here. A caller that wants every published message
 * therefore has to read both: the callback for single-frame messages, this for longer ones. The
 * split is deliberate, and keeps a one-frame publish on the same low-latency path it has always
 * had rather than making it wait for a tick.
 *
 * The one exception is a message this node published to a topic it subscribes to itself: nothing
 * echoes a node's own frames back to it, so a multi-frame self-publish is staged here on
 * completion.
 *
 * @param context Pointer to the artie_can_context_t struct representing the context.
 * @param out Pointer to the artie_can_psacp_message_t to copy the message into.
 * @return ARTIE_CAN_ERR_NONE if a message was written to out, ARTIE_CAN_ERR_NO_DATA if none was
 * ready, or ARTIE_CAN_ERR_INVALID_ARG on a bad argument.
 */
artie_can_error_t artie_can_psacp_get_message(artie_can_context_t *context, artie_can_psacp_message_t *out);

/**
 * @brief Number of inbound messages this node has dropped rather than delivered incomplete.
 *
 * Counts every message discarded by reassembly: a missing or out-of-order fragment, a message
 * larger than this node's reassembly slot, a slot aged out before its PUB_END arrived, and a
 * message that arrived with no free slot to put it in. A steadily climbing count means this node
 * is not keeping up with the bus, which no amount of publishing-side retry would fix.
 *
 * @param context Pointer to the artie_can_context_t struct representing the context.
 * @return The number of dropped messages since initialization, or 0 if context is NULL.
 */
uint32_t artie_can_psacp_dropped_count(const artie_can_context_t *context);

/**
 * @brief Handle a received PSACP frame within an ISR context.
 * Checks the frame's topic against the node's subscriptions and calls the rx_callback if matched.
 *
 * @param context Pointer to the artie_can_context_t struct representing the context.
 * @param frame Pointer to the artie_can_frame_t struct representing the received frame.
 */
void psacp_receive_in_isr(artie_can_context_t *context, const artie_can_frame_t *frame);

/**
 * @brief Tick function for the PSACP protocol. Since PSACP is fire-and-forget with no state machine,
 * this function currently does nothing and always returns ARTIE_CAN_ERR_NONE.
 *
 * @param handle Pointer to the artie_can_backend_t struct representing the backend.
 * @return artie_can_error_t Always returns ARTIE_CAN_ERR_NONE.
 */
artie_can_error_t psacp_tick(artie_can_backend_t *handle);
