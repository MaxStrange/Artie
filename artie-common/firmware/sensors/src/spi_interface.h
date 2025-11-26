/**
 * @file This module contains the SPI functions common to all the sensors that use it.
 */
#pragma once

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>

/** Simple blocking read. Suitable to be run from an interrupt context if necessary. */
void myspi_blocking_read(uint8_t cs_pin, uint8_t reg, uint8_t *buf, uint16_t len);

/** Simple blocking write. Suitable to be run from an interrupt context if necessary. */
void myspi_blocking_write(uint8_t cs_pin, uint8_t reg, uint8_t byte);

#ifdef __cplusplus
}
#endif
