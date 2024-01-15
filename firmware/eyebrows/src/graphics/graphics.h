/**
 * @file graphics.h
 * @brief High-level interface to the LCD display.
 *
 */
#pragma once

#include "../cmds/cmds.h"
#include "../board/pinconfig.h"
#include "../board/types.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Initialize graphics (and LCD) libraries.
 *
 * @param side The side (left or right) that this MCU controls.
 *
 */
void graphics_init(side_t side);

/**
 * @brief Handles the given LCD subsystem command.
 *
 * @param command The command to handle.
 */
void graphics_cmd(cmd_t command);

#ifdef __cplusplus
}
#endif
