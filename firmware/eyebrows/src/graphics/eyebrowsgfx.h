/**
 * @file eyebrowsgfx.h
 * @brief Eyebrows-specific graphics stuff.
 *
 */
#pragma once

#ifdef __cplusplus
extern "C" {
#endif

#include "../cmds/cmds.h"
#include "../board/types.h"

/**
 * @brief Initialize graphics (and LCD) libraries.
 *
 * @param side Whether this MCU is left or right eyebrow.
 */
void eyebrowsgfx_init(side_t side);

/**
 * @brief Handles the given LCD subsystem command.
 *
 * @param command The command to handle.
 * The LCD subsystem typically works like this:
 * command is xxxyyy (after the subsystem mask is removed),
 * where each of the three x's and y's refers to one of the
 * three pairs of vertices which make up the eyebrow.
 * In the case the y is set to 1, the eyebrow vertex pair
 * at that location (left, middle, right) is UP. If it is set
 * to 0, then it is DOWN.
 * However, if the corresponding x is set, it means either
 * we should ignore the y and set the vertex pair to the middle,
 * OR we have a special command. If x is set and y is also set,
 * then it is a special command. If x is set and y is cleared,
 * then we ignore the y and set the vertex pair to middle.
 */
void eyebrowsgfx_cmd(cmd_t command);

#ifdef __cplusplus
}
#endif
