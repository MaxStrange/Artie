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
#include "../board/types.h"

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

#ifdef __cplusplus
}
#endif
