/*
 * Typedefs for this project.
 */
#pragma once

#ifdef __cplusplus
extern "C" {
#endif

/** Which eyebrow are we? */
typedef enum {
    EYE_LEFT_SIDE           = 0,
    EYE_RIGHT_SIDE          = 1,
    EYE_UNASSIGNED_SIDE     = 0xFF
} side_t;

// Commands are of the form xxyy yyyy where xx are two bits which set the module
//    and yy yyyy are six bits which specify the command.

#define CMD_MODULE_ID_LEDS  0x00        // 0b0000 0000
#define CMD_MODULE_ID_LCD   0x40        // 0b0100 0000
#ifndef MOUTH
    #define CMD_MODULE_ID_SERVO    0x80    // 0b1000 0000 // Exclusive to eyes
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
    CMD_LCD_MOUTH_TALK              = (CMD_MODULE_ID_LCD        | 0x07),
#else
    CMD_LCD_DRAW                    = (CMD_MODULE_ID_LCD        | 0x30),    // See eyebrowsgfx.h for the schema
    // Commands for servos
    CMD_SERVO_TURN                  = (CMD_MODULE_ID_SERVO      | 0x3F)     // Servo commands accept 6 bits converted to degrees of rotation
#endif // MOUTH
} cmd_t;

#ifdef __cplusplus
}
#endif
