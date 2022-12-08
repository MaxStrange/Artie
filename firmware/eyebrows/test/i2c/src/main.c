// LCD makes use of i2c1, so we need to use i2c0
// Use GP21 (physical pin 27) for SCL and GP20 (physical pin 26) for SDA
// Use onboard LED.
// Use USB for power and UART connection.
// Connect this test over I2C to an Arduino Micro, get that to work, then connect to RPi and get that to work.
// !! You need a level shifter for both examples !!

// Stdlib includes
#include <stdint.h>
#include <stdbool.h>
// SDK includes
#include "hardware/i2c.h"
#include "pico/stdlib.h"
// Third party library includes
#include <i2c_fifo.h>
#include <i2c_slave.h>

/** Baudrate for the I2C bus */
static const uint I2C_BAUDRATE = 100 * 1000;

/** Our I2C address */
static const uint OUR_I2C_ADDRESS = 0x17;

/** Our SDA pin */
static const uint I2C_SDA_PIN = 20;

/** Our SCL pin */
static const uint I2C_SCL_PIN = 21;

/** Our LED pin (onboard LED) */
static const uint LED_PIN = 25;

// These are the pins that the LCD uses
// #define LCD_RST_PIN  12
// #define LCD_DC_PIN   8
// #define LCD_BL_PIN   13
//
// #define LCD_CS_PIN   9
// #define LCD_CLK_PIN  10
// #define LCD_MOSI_PIN 11
//
// #define LCD_SCL_PIN  7
// #define LCD_SDA_PIN  6


//VCC	VSYS	Power Input
//GND	GND	    Ground
//DIN	GP11	MOSI pin of SPI, data transmitted from Master t Slave
//CLK	GP10	SCK pin of SPI, clock pin
//CS	GP9	    Chip selection of SPI, low active
//DC	GP8	    Data/Command control pin (High for data; Low for command)
//RST	GP12	Reset pin, low active
//BL	GP13	Backlight control
//KEY0	GP15	User button KEY0
//KEY1	GP17	User button KEY1
//KEY2	GP2	    User button KEY2
//KEY3	GP3	    User button KEY3


/** The commands we understand over I2C */
typedef enum {
    LED_ON = 0x00,
    LED_OFF = 0x01
} cmd_t;

/** If we get an unexpected value on the I2C bus, we'll put it here for printing in main loop */
static err_byte = 0;

/** Helper function for ISR. Called when we want to read bytes from the controller. */
static inline void _isr_receive_bytes(i2c_inst_t *i2c)
{
    size_t nbytes = i2c_get_read_available(i2c);
    for (size_t i = 0; i < nbytes; i++)
    {
        uint byte = i2c_read_byte(i2c);
        switch (byte)
        {
            case LED_ON:
                gpio_put(LED_PIN, 1);
                break;
            case LED_OFF:
                gpio_put(LED_PIN, 0);
                break;
            default:
                // Shouldn't happen
                err_byte = byte;
                break;
        }
    }
}

/**
 * @brief Handler for the I2C slave (us) interrupt.
 *
 * @param i2c
 * @param event
 */
static void _i2c_handler(i2c_inst_t *i2c, i2c_slave_event_t event)
{
    switch (event)
    {
        case I2C_SLAVE_RECEIVE: // master has written some data
            _isr_receive_bytes(i2c);
            break;
        case I2C_SLAVE_REQUEST: // master is requesting data
            // TODO: This shouldn't happen
            break;
        case I2C_SLAVE_FINISH: // master has signalled Stop / Restart
            break;
        default:
            break;
    }
}

int main(void)
{
    // Initialize UART
    stdio_init_all();

    // Initialize I2C as slave
    gpio_init(I2C_SDA_PIN);
    gpio_init(I2C_SCL_PIN);
    gpio_set_function(I2C_SDA_PIN, GPIO_FUNC_I2C);
    gpio_set_function(I2C_SCL_PIN, GPIO_FUNC_I2C);
    gpio_pull_up(I2C_SDA_PIN);
    gpio_pull_up(I2C_SCL_PIN);
    i2c_init(i2c0, I2C_BAUDRATE);
    i2c_slave_init(i2c0, OUR_I2C_ADDRESS, &_i2c_handler);

    // Initialize LED pin
    gpio_init(LED_PIN);
    gpio_set_dir(LED_PIN, GPIO_OUT);

    while (true)
    {
        // Check on error
        uint err = err_byte;
        if (err)
        {
            printf("Got an unexpected byte over i2c: 0x%02X\n", err);
        }
    }

    return 0;
}
