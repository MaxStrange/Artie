#include <i2c_fifo.h>
#include <i2c_slave.h>
#include <pico/stdlib.h>
#include <stdio.h>
#include <string.h>

static const uint I2C_SLAVE_ADDRESS = 0x17;
static const uint I2C_BAUDRATE = 100000; // 100 kHz

// For this example, we run both the master and slave from the same board.
// You'll need to wire pin GP4 to GP6 (SDA), and pin GP5 to GP7 (SCL).
static const uint I2C_SLAVE_SDA_PIN = PICO_DEFAULT_I2C_SDA_PIN; // 4
static const uint I2C_SLAVE_SCL_PIN = PICO_DEFAULT_I2C_SCL_PIN; // 5
static const uint I2C_MASTER_SDA_PIN = 6;
static const uint I2C_MASTER_SCL_PIN = 7;
static const uint LED_PIN = 25;

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
            break;
        case I2C_SLAVE_FINISH: // master has signalled Stop / Restart
            break;
        default:
            break;
    }
}

static void setup_slave() {
    gpio_init(I2C_SLAVE_SDA_PIN);
    gpio_set_function(I2C_SLAVE_SDA_PIN, GPIO_FUNC_I2C);
    gpio_pull_up(I2C_SLAVE_SDA_PIN);

    gpio_init(I2C_SLAVE_SCL_PIN);
    gpio_set_function(I2C_SLAVE_SCL_PIN, GPIO_FUNC_I2C);
    gpio_pull_up(I2C_SLAVE_SCL_PIN);

    i2c_init(i2c0, I2C_BAUDRATE);
    i2c_slave_init(i2c0, I2C_SLAVE_ADDRESS, &_i2c_handler);
}

static void run_master() {
    gpio_init(I2C_MASTER_SDA_PIN);
    gpio_set_function(I2C_MASTER_SDA_PIN, GPIO_FUNC_I2C);
    gpio_pull_up(I2C_MASTER_SDA_PIN);

    gpio_init(I2C_MASTER_SCL_PIN);
    gpio_set_function(I2C_MASTER_SCL_PIN, GPIO_FUNC_I2C);
    gpio_pull_up(I2C_MASTER_SCL_PIN);

    i2c_init(i2c1, I2C_BAUDRATE);

    uint8_t buf[1] = {0x00};
    while (true) {
        int count = i2c_write_blocking(i2c1, I2C_SLAVE_ADDRESS, buf, 1, false);
        if (count < 0) {
            puts("Couldn't write to slave.\n");
            while (true) {
                ; // Trap
            }
        }
        buf[0] = (buf[0] == 0x01) ? 0x00 : 0x01;
        sleep_ms(1000);

        uint8_t err = err_byte;
        if (err_byte) {
            printf("Got an unexpected byte over i2c: 0x%02X\n", err);
        }
    }
}

int main() {
    stdio_init_all();
    puts("\nI2C slave example");

    // Initialize LED pin
    gpio_init(LED_PIN);
    gpio_set_dir(LED_PIN, GPIO_OUT);

    setup_slave();
    run_master();
}
