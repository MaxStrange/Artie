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
void leds_init(uint led_pin);

/** Turn the LED on. */
void leds_on(void);

/** Turn the LED off. */
void leds_off(void);

/** Turn the LED to heartbeat mode. */
void leds_heartbeat(void);

#ifdef __cplusplus
}
#endif
