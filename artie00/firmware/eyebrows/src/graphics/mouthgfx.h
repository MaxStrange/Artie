/**
 * @file mouthgfx.h
 * @brief Mouth-specific graphics stuff.
 *
 */
#pragma once

#ifdef __cplusplus
extern "C" {
#endif

#ifdef MOUTH

#include "../board/types.h"

/**
 * @brief Initialize graphics (and LCD) libraries.
 */
void mouthgfx_init(void);

/**
 * @brief Handles the given LCD subsystem command.
 *
 * @param command The command to handle.
 */
void mouthgfx_cmd(cmd_t command);

#endif

#ifdef __cplusplus
}
#endif
