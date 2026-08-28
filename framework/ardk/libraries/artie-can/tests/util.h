/**
 * @file util.h
 * @brief Utility functions and definitions for Artie CAN tests.
 *
 */

#pragma once

#include <stdbool.h>
#include <stdint.h>
#include "artie_can.h"

/** Good ol' array length macro. */
#define ARRAY_LENGTH(arr) (sizeof(arr) / sizeof((arr)[0]))

/**
 * @brief Test that two CAN frames are equal.
 *
 * @param frame1 The first CAN frame to compare.
 * @param frame2 The second CAN frame to compare.
 */
void assert_frames_equal(volatile const artie_can_frame_t *frame1, volatile const artie_can_frame_t *frame2);

/**
 * @brief Test that two RTACP frames are equal.
 *
 * @param frame1 The first RTACP frame to compare.
 * @param frame2 The second RTACP frame to compare.
 */
void assert_rtacp_frames_equal(volatile const artie_can_frame_rtacp_t *frame1, volatile const artie_can_frame_rtacp_t *frame2);

/**
 * @brief Get the current time in ms.
 *
 * @return uint64_t Time in ms.
 */
uint64_t get_current_time_ms(void);

/**
 * @brief Get a multicast group address that no other test process is using.
 *
 * The suites simulate a CAN bus over UDP multicast, and multicast does not respect process
 * boundaries: every listener joined to a group and port sees every frame sent to it, whoever sent
 * it. A fixed group therefore makes two concurrent test runs one shared bus - and since every
 * suite uses the same node addresses, each run sees the other's frames as though they were its
 * own. The result is NACK storms and transfers that abort, reported as a failing test that has
 * nothing wrong with it.
 *
 * That is not hypothetical: the artie-tool test task runs the suite on Docker's default bridge
 * network, which is shared, so two runs on one host - two CI jobs, or a developer running the
 * suite while a job runs - collide.
 *
 * This derives the group from the process ID so each test process gets its own bus. Set
 * ARTIE_CAN_TEST_MCAST_GROUP to override, which is useful when watching traffic with an external
 * tool.
 *
 * @param out Buffer to write the dotted-quad group address into.
 * @param out_size Size of out; must be at least 16 bytes.
 * @param suite_id Small per-suite number, so suites in one process never share a group either.
 * @return out, for convenience in an initializer.
 */
const char *test_multicast_group(char *out, size_t out_size, uint8_t suite_id);

/**
 * @brief Wait for a condition to become true with a timeout.
 *
 * @param condition Pointer to a volatile boolean that represents the condition we are waiting for.
 * @param timeout_ms The timeout in milliseconds to wait for the condition to become true.
 * @param tick_callback Optional callback function to call periodically (~1ms intervals) while waiting. Can be NULL.
 * @return artie_can_error_t Error code indicating whether the condition became true or if we timed out.
 */
artie_can_error_t wait_with_timeout(volatile bool *condition, uint32_t timeout_ms, void (*tick_callback)(void));
