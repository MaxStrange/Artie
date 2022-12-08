// Stdlib includes
#include <stdint.h>
#include <stdbool.h>
// SDK includes
#include "hardware/i2c.h"
#include "pico/stdlib.h"
#include "pico/util/queue.h"
// Third party library includes
#include <i2c_fifo.h>
#include <i2c_slave.h>
// Local includes
#include "cmds.h"
#include "../board/pinconfig.h"
#include "../board/errors.h"

/** I2C address if we are the left eye. */
static const uint LEFT_EYE_I2C_ADDRESS = 0x17;

/** I2C address if we are the right eye. */
static const uint RIGHT_EYE_I2C_ADDRESS = 0x18;

/** Baudrate for the I2C bus */
static const uint I2C_BAUDRATE = 100 * 1000;

/** Our I2C address */
static const uint OUR_I2C_ADDRESS = EYE_UNASSIGNED_SIDE;

/** The number of items we can hold at maximum in the command queue. No testing was done to determine this value. */
static const uint CMD_QUEUE_SIZE = 128;

/** The circular buffer of commands we've received so far. */
static queue_t cmd_queue;

/** Helper function for ISR. Called when we want to read bytes from the controller. */
static inline void _isr_receive_bytes(i2c_inst_t *i2c)
{
    size_t nbytes = i2c_get_read_available(i2c);
    for (size_t i = 0; i < nbytes; i++)
    {
        uint8_t byte = i2c_read_byte(i2c);
        bool added = queue_try_add(&cmd_queue, &byte);
        if (!added)
        {
            errno = ERR_ID_CMD_MODULE | ENOMEM;
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
        errno = ERR_ID_CMD_MODULE | EIO;
        break;
    case I2C_SLAVE_FINISH: // master has signalled Stop / Restart
        break;
    default:
        break;
    }
}

side_t cmds_init(void)
{
    log_info("Init command module\n");

    // Determine if we are right or left eyebrow/eye
    // Read state: HIGH (1) means we are RIGHT
    //              LOW (0) means we are LEFT
    gpio_init(ADDRESS_PIN);
    gpio_set_dir(ADDRESS_PIN, GPIO_IN);
    side_t left_or_right = gpio_get(ADDRESS_PIN);
    OUR_I2C_ADDRESS = (left_or_right == EYE_LEFT_SIDE) ? LEFT_EYE_I2C_ADDRESS : RIGHT_EYE_I2C_ADDRESS;

    // Initialize I2C
    queue_init(&cmd_queue, sizeof(uint8_t), CMD_QUEUE_SIZE);
    gpio_init(I2C_SDA_PIN);
    gpio_init(I2C_SCL_PIN);
    gpio_set_function(I2C_SDA_PIN, GPIO_FUNC_I2C);
    gpio_set_function(I2C_SCL_PIN, GPIO_FUNC_I2C);
    gpio_pull_up(I2C_SDA_PIN);
    gpio_pull_up(I2C_SCL_PIN);

    i2c_init(i2c0, I2C_BAUDRATE);
    assert(OUR_I2C_ADDRESS != EYE_UNASSIGNED_SIDE);
    i2c_slave_init(i2c0, OUR_I2C_ADDRESS, &_i2c_handler);

    return left_or_right;
}

bool cmds_get_next(cmd_t *ret)
{
    uint32_t ret_as_uint32 = 0;
    bool worked = queue_try_remove(&cmd_queue, &ret_as_uint32);
    if (worked)
    {
        *ret = (uint8_t)ret_as_uint32;
    }
    return worked;
}
