// Stdlib includes
#include <stdbool.h>
#include <stdio.h>
// SDK includes
#include "pico/stdlib.h"
// Library includes
#include <leds.h>
#include <errors.h>
// Local includes
#include "board/pinconfig.h"
#include "board/types.h"

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

    while (true)
    {
        // TODO
        // Contract is this:
        //      Controller Module tells us who to reset, then we handle the reset logic asynchronously.
    }
}
