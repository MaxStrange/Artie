/**
 * @file leds.h
 * @brief LED module.
 *
 */
#pragma once

#include "../cmds/cmds.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Initializes the LEDs.
 *
 */
void leds_init(void);

/**
 * @brief Handle the given LED subsystem command.
 *
 * @param command The command to handle.
 */
void leds_cmd(cmd_t command);

#ifdef __cplusplus
}
#endif
