// Std lib includes
#include <stdio.h>
// SDK includes
#include "hardware/gpio.h"
// Local includes
#include "leds.h"
#include "../board/pinconfig.h"
#include "../cmds/cmds.h"
#include "../board/errors.h"

static void leds_on(void)
{
    gpio_put(LED_PIN, 1);
}

static void leds_off(void)
{
    gpio_put(LED_PIN, 0);
}

static void leds_heartbeat(void)
{
    // TODO: Set up a PWM signal and a timer interrupt for increasing and decreasing.
}

void leds_init(void)
{
    log_info("Init LEDs\n");
    gpio_init(LED_PIN);
    gpio_set_dir(LED_PIN, GPIO_OUT);
}

void leds_cmd(cmd_t command)
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
