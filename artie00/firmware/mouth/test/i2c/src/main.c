// Stdlib includes
#include <stdbool.h>
#include <stdio.h>
// SDK includes
#include "pico/stdlib.h"
// Local includes
#include "graphics/graphics.h"
#include "leds/leds.h"
#include "cmds/cmds.h"
#include "board/errors.h"

int main()
{
    // Initialize UART for debugging (in a release build, this should be turned off from the CMake build system)
    stdio_init_all();

    // Initialize GPIO pins for LEDs
    leds_init();

    // Initialize I2C for communication with controller module. If we are mouth, left_or_right is unassigned.
    side_t left_or_right = cmds_init();

    // Initialize LCD
    graphics_init(left_or_right);

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
                default:
                    log_error("Illegal cmd type 0x%02X; route mask is: 0x%02X\n", command, route);
                    break;
            }
        }
    }
}
