/**
 * @file cmds.h
 * @brief Command module.
 * This module is responsible for initializing the interface
 * to the controlling module and for accepting commands
 * and interpreting them.
 *
 */
#pragma once

#ifdef __cplusplus
extern "C" {
#endif

#include <stdbool.h>

#define CMD_MODULE_ID_LEDS  0x00        // 0b0000 0000
#define CMD_MODULE_ID_LCD   0x40        // 0b0100 0000
#define CMD_MODULE_ID_SERVO 0x80        // 0b1000 0000
//#define CMD_MODULE_ID_??    0xC0      // If you need one more subsystem, this is the address

/**
 * @brief The types of commands we can receive and act on.
 *
 */
typedef enum {
    CMD_LED_ON          = (CMD_MODULE_ID_LEDS   | 0x00),
    CMD_LED_OFF         = (CMD_MODULE_ID_LEDS   | 0x01),
    CMD_LED_HEARTBEAT   = (CMD_MODULE_ID_LEDS   | 0x02),
    CMD_LCD_TEST        = (CMD_MODULE_ID_LCD    | 0x11),
    CMD_LCD_OFF         = (CMD_MODULE_ID_LCD    | 0x22),
    CMD_LCD_DRAW        = (CMD_MODULE_ID_LCD    | 0x30),    // See graphics.h for the schema
    CMD_SERVO_TURN      = (CMD_MODULE_ID_SERVO  | 0x3F)     // Servo commands accept 6 bits converted to degrees of rotation
} cmd_t;

/**
 * @brief Initialize the command module.
 */
void cmds_init(void);

/**
 * @brief Get the next command from the queue of so-far received commands.
 * This does not block. If there is no command, we return false. Otherwise,
 * we return true and fill the pointer.
 *
 * @return bool True if a command was returned, otherwise false.
 */
bool cmds_get_next(cmd_t *ret);

#ifdef __cplusplus
}
#endif
