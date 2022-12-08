/**
 * @file servo.h
 * @brief Interface to the servo subsystem. The servo controls the eye socket.
 *
 */
#pragma once

#ifdef __cplusplus
extern "C" {
#endif

#include "../cmds/cmds.h"

/**
 * @brief Initialize the servo subsystem.
 *
 */
void servo_init(void);

/**
 * @brief Handle the given command meant for the servo subsystem.
 *
 * @param command Servo command to handle.
 */
void servo_cmd(cmd_t command);

/**
 * @brief Run the servo all the way to the limit switch on the left, taking
 *        note of farthest we can go.
 *        Then do the same thing on the right.
 */
void calibrate_servo(void);

#ifdef __cplusplus
}
#endif
