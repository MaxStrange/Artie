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

// Standard libraries
#include <stdbool.h>
// SDK includes
#include "pico/stdlib.h"

/** Set the i2c register for reading. */
void cmds_set_register_value(float value);

/**
 * @brief Initialize the command module.
 *
 * @param i2c_address The address of this MCU on the I2C bus.
 */
void cmds_init(uint i2c_address, uint sda_pin, uint scl_pin);

/**
 * @brief Get the next command from the queue of so-far received commands.
 * This does not block. If there is no command, we return false. Otherwise,
 * we return true and fill the pointer.
 *
 * @return bool True if a command was returned, otherwise false.
 */
bool cmds_get_next(uint8_t *ret);

#ifdef __cplusplus
}
#endif
