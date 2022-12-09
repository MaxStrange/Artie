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

// Commands are of the form xxyy yyyy where xx are two bits which set the module
//    and yy yyyy are six bits which specify the command.

#define CMD_MODULE_ID_LEDS  0x00        // 0b0000 0000
#define CMD_MODULE_ID_LCD   0x40        // 0b0100 0000
#ifdef MOUTH
    #define CMD_MODULE_ID_SENSORS  0x80    // 0b1000 0000 // Exclusive to mouth
#else
    #define CMD_MODULE_ID_SERVO    0x80    // 0b1000 0000 // Exclusive to eyes
#endif // MOUTH

#ifndef MOUTH
    /** Which eyebrow are we? */
    typedef enum {
        EYE_LEFT_SIDE           = 0,
        EYE_RIGHT_SIDE          = 1,
        EYE_UNASSIGNED_SIDE     = 0xFF
    } side_t;
#endif // MOUTH

/**
 * @brief The types of commands we can receive and act on.
 *
 */
typedef enum {
    // Commands for LED
    CMD_LED_ON                      = (CMD_MODULE_ID_LEDS       | 0x00),
    CMD_LED_OFF                     = (CMD_MODULE_ID_LEDS       | 0x01),
    CMD_LED_HEARTBEAT               = (CMD_MODULE_ID_LEDS       | 0x02),
    // Commands for LCD
    CMD_LCD_TEST                    = (CMD_MODULE_ID_LCD        | 0x11),
    CMD_LCD_OFF                     = (CMD_MODULE_ID_LCD        | 0x22),
#ifdef MOUTH
    CMD_LCD_MOUTH_SMILE             = (CMD_MODULE_ID_LCD        | 0x00),
    CMD_LCD_MOUTH_FROWN             = (CMD_MODULE_ID_LCD        | 0x01),
    CMD_LCD_MOUTH_LINE              = (CMD_MODULE_ID_LCD        | 0x02),
    CMD_LCD_MOUTH_SMIRK             = (CMD_MODULE_ID_LCD        | 0x03),
    CMD_LCD_MOUTH_OPEN              = (CMD_MODULE_ID_LCD        | 0x04),
    CMD_LCD_MOUTH_OPEN_SMILE        = (CMD_MODULE_ID_LCD        | 0x05),
    CMD_LCD_MOUTH_ZIG_ZAG           = (CMD_MODULE_ID_LCD        | 0x06),
#else
    CMD_LCD_DRAW                    = (CMD_MODULE_ID_LCD        | 0x30),    // See eyebrowsgfx.h for the schema
#endif // MOUTH
#ifdef MOUTH
    // Commands for sensors
    CMD_SENSORS_READ_TEMPERATURE    = (CMD_MODULE_ID_SENSORS    | 0x00),
    CMD_SENSORS_READ_HUMIDITY       = (CMD_MODULE_ID_SENSORS    | 0x01),
    CMD_SENSORS_READ_PRESSURE       = (CMD_MODULE_ID_SENSORS    | 0x02),
    CMD_SENSORS_READ_ACCEL_X        = (CMD_MODULE_ID_SENSORS    | 0x03),
    CMD_SENSORS_READ_ACCEL_Y        = (CMD_MODULE_ID_SENSORS    | 0x04),
    CMD_SENSORS_READ_ACCEL_Z        = (CMD_MODULE_ID_SENSORS    | 0x05),
    CMD_SENSORS_READ_GYRO_X         = (CMD_MODULE_ID_SENSORS    | 0x06),
    CMD_SENSORS_READ_GYRO_Y         = (CMD_MODULE_ID_SENSORS    | 0x07),
    CMD_SENSORS_READ_GYRO_Z         = (CMD_MODULE_ID_SENSORS    | 0x08)
#else
    // Commands for servos
    CMD_SERVO_TURN                  = (CMD_MODULE_ID_SERVO      | 0x3F)     // Servo commands accept 6 bits converted to degrees of rotation
#endif // MOUTH
} cmd_t;

/** Set the i2c register for reading. */
void cmds_set_register_value(float value);

/**
 * @brief Initialize the command module, which determines which MCU we are.
 */
side_t cmds_init(void);

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
