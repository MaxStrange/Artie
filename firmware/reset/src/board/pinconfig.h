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
static const uint I2C_SDA_PIN = 2;

/** I2C SCL pin used for communicating with controller module */
static const uint I2C_SCL_PIN = 3;

#ifdef __cplusplus
}
#endif
