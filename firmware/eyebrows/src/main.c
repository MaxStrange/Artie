// Stdlib includes
#include <stdbool.h>
#include <stdio.h>
// SDK includes
#include "pico/stdlib.h"
// Library includes
#include <errors.h>
#include <leds.h>
// Local includes
#include "cmds/cmds.h"
#include "graphics/graphics.h"
#include "board/pinconfig.h"
#ifndef MOUTH
    #include "servo/servo.h"
#endif // MOUTH

#ifdef MOUTH
/** I2C address if we are the mouth. */
static const uint MOUTH_I2C_ADDRESSS = 0x19;
#else
/** I2C address if we are the left eye. */
static const uint LEFT_EYE_I2C_ADDRESS = 0x17;

/** I2C address if we are the right eye. */
static const uint RIGHT_EYE_I2C_ADDRESS = 0x18;
#endif // MOUTH

/**
 * @brief Determine which 'side' we are.
 *
 * @return side_t
 */
static side_t determine_side(void)
{
#ifdef MOUTH
    return EYE_UNASSIGNED_SIDE
#endif
    // Determine if we are right or left eyebrow/eye
    // Read state: HIGH (1) means we are RIGHT
    //              LOW (0) means we are LEFT
    gpio_init(ADDRESS_PIN);
    gpio_set_dir(ADDRESS_PIN, GPIO_IN);
    side_t left_or_right = (side_t)gpio_get(ADDRESS_PIN);
    return left_or_right;
}

/**
 * @brief Determine our I2C address.
 *
 * @return The I2C address of this MCU on the bus.
 */
static inline uint determine_address(side_t side)
{
    switch (side)
    {
        case EYE_LEFT_SIDE:
            return LEFT_EYE_I2C_ADDRESS;
        case EYE_RIGHT_SIDE:
            return RIGHT_EYE_I2C_ADDRESS;
        default:
#ifdef MOUTH
            return MOUTH_I2C_ADDRESSS;
#else
            return LEFT_EYE_I2C_ADDRESS;
#endif // MOUTH
    }
}

/**
 * @brief Command table for the LED subsystem.
 *
 * @param command
 */
static void leds_cmd(cmd_t command)
{
    switch (command)
    {
        case CMD_LED_ON:
            leds_on();
            break;
        case CMD_LED_OFF:
            leds_off();
            break;
        case CMD_LED_HEARTBEAT:
            leds_heartbeat();
            break;
        default:
            log_error("Illegal cmd type 0x%02X\n in LED subsystem", command);
            break;
    }
}

int main()
{
    // Initialize UART for debugging (in a release build, this should be turned off from the CMake build system)
    stdio_init_all();

    // Initialize GPIO pins for LEDs
    leds_init(LED_PIN);

    // Determine which 'side' we are (LEFT, RIGHT, MOUTH)
    const side_t side = determine_side();

    // Determine our I2C address
    const uint address = determine_address(side);

    // Initialize I2C for communication with controller module.
    cmds_init(address);

    // Initialize LCD
    graphics_init(side);

#ifndef MOUTH
    // Initialize servo subsystem
    servo_init();
#endif // MOUTH

    while (true)
    {
        // Check the errno
        err_t e = errno;
        if (e)
        {
            uint8_t flag = (uint8_t)(e & 0x00FF);
            uint8_t module = (uint8_t)((e & 0xFF00) >> 8);
            log_error("Error flag: 0x%02X from module with ID: 0x%02X\n", flag, module);
            errno = 0x0000;
        }

        // Get the next command out of the cmds module and act on it.
        cmd_t command;
        if (cmds_get_next(&command))
        {
            // Mask off the first two bits to detect the route
            uint8_t route = command & 0xC0;
            switch (route)
            {
                case CMD_MODULE_ID_LEDS:
                    log_debug("LED command\n");
                    leds_cmd(command);
                    break;
                case CMD_MODULE_ID_LCD:
                    log_debug("LCD command\n");
                    graphics_cmd(command);
                    break;
#ifndef MOUTH
                case CMD_MODULE_ID_SERVO:
                    log_debug("Servo command\n");
                    servo_cmd(command);
                    break;
#endif // MOUTH
                default:
                    log_error("Illegal cmd type 0x%02X; route mask is: 0x%02X\n", command, route);
                    break;
            }
        }
    }
}
