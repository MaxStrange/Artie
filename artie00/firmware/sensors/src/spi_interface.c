// Stdlib
#include <stdint.h>
// SDK
#include "hardware/gpio.h"
#include "hardware/spi.h"
// Local
#include "spi_interface.h"

/** CS pull down with a few no-ops to ensure compatability with the sensor's timing. */
static inline void cs_select(uint8_t pin) {
    asm volatile("nop \n nop \n nop");
    gpio_put(pin, 0);
    asm volatile("nop \n nop \n nop");
}

/** CS pull up with a few no-ops to ensure compatability with the sensor's timing. */
static inline void cs_deselect(uint8_t pin) {
    asm volatile("nop \n nop \n nop");
    gpio_put(pin, 1);
    asm volatile("nop \n nop \n nop");
}

/** Simple blocking read. Suitable to be run from an interrupt context if necessary. */
void myspi_blocking_read(uint8_t cs_pin, uint8_t reg, uint8_t *buf, uint16_t len)
{
    cs_select(cs_pin);
    spi_write_blocking(spi0, &reg, 1);
    // Need about 50 ns of NOPs here
    // Clock rate is 130 MHz out of the box and we don't change it so need about 3 noops to make sure
    asm volatile("nop \n nop \n nop");
    spi_read_blocking(spi0, 0, buf, len);
    cs_deselect(cs_pin);
}

/** Simple blocking write. */
void myspi_blocking_write(uint8_t cs_pin, uint8_t reg, uint8_t byte)
{
    uint8_t buf[2] = {reg, byte};

    cs_select(cs_pin);
    spi_write_blocking(spi0, buf, 2);
    cs_deselect(cs_pin);
}
