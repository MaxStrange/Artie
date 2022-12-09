/*
 * Pin configuration for the eyebrows.
 */
#pragma once

#ifdef __cplusplus
extern "C" {
#endif

#include <pico/stdlib.h>

/** The LED pin used for testing and heartbeat signal */
static const uint LED_PIN = 25; // on board LED

/** I2C SDA pin used for communicating with controller module */
static const uint I2C_SDA_PIN = 20;

/** I2C SCL pin used for communicating with controller module */
static const uint I2C_SCL_PIN = 21;

/** Servo PWM pin. Used for controlling the attached servo. */
static const uint SERVO_PWM_PIN = 15;

/** Limit switch GPIO interrupt pin to tell us servo has gone to limit on left side. */
static const uint LIMIT_SWITCH_LEFT = 18;

/** Limit switch GPIO interrupt pin to tell us servo has gone to limit on right side. */
static const uint LIMIT_SWITCH_RIGHT = 19;

/** This pin tells us whether we are left or right. */
static const uint ADDRESS_PIN = 22;

// These are used by the LCD subsystem and defined in the LCD library.
//#define LCD_RST_PIN  12
//#define LCD_DC_PIN   8
//#define LCD_BL_PIN   13
//
//#define LCD_CS_PIN   9
//#define LCD_CLK_PIN  10
//#define LCD_MOSI_PIN 11
//
//#define LCD_SCL_PIN  7
//#define LCD_SDA_PIN  6
//
// They make use of spi1 and i2c1

#ifdef __cplusplus
}
#endif
