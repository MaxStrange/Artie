/*
 * Pin configuration for the eyebrows.
 */
#pragma once

#ifdef __cplusplus
extern "C" {
#endif

#include <pico/stdlib.h>

// Commands are of the form xxyy yyyy where xx are two bits which set the module
//    and yy yyyy are six bits which specify the command.

#define CMD_MODULE_ID_LEDS  0x00        // 0b0000 0000

/**
 * @brief The types of commands we can receive and act on.
 *
 */
typedef enum {
    // Commands for LED
    CMD_LED_ON                      = (CMD_MODULE_ID_LEDS       | 0x00),
    CMD_LED_OFF                     = (CMD_MODULE_ID_LEDS       | 0x01),
    CMD_LED_HEARTBEAT               = (CMD_MODULE_ID_LEDS       | 0x02),
} cmd_t;

#ifdef __cplusplus
}
#endif
