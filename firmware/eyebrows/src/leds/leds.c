// Std lib includes
#include <stdio.h>
// SDK includes
#include "hardware/gpio.h"
#include "hardware/irq.h"
#include "hardware/pwm.h"
// Local includes
#include "leds.h"
#include "../board/pinconfig.h"
#include "../cmds/cmds.h"
#include "../board/errors.h"

/** Possible modes of the LED. */
typedef enum {
    LED_MODE_UNASSIGNED,    // Default value for LED before we have initialized.
    LED_MODE_ON_OFF,        // The LED must be turned on or off explicitly through the command interface while in this mode.
    LED_MODE_HEARTBEAT,     // The LED displays a fade in/fade out pattern while in this mode.
} led_mode_t;

/** Depending on the mode of LED we want, the LED pin must be configured differently. */
static led_mode_t led_mode = LED_MODE_UNASSIGNED;

/** Deconfigure LED pin from ON/OFF mode. */
static inline void deconfigure_led_on_off_mode(void)
{
    gpio_init(LED_PIN);
}

/** Deconfigure LED pin from heartbeat mode. */
static inline void deconfigure_led_heartbeat_mode(void)
{
    uint slice_num = pwm_gpio_to_slice_num(LED_PIN);
    pwm_set_enabled(slice_num, false);
    pwm_set_irq_enabled(slice_num, false);
    irq_set_enabled(PWM_IRQ_WRAP, false);
    gpio_init(LED_PIN);
}

/** Configure LED pin for ON/OFF mode. */
static inline void configure_led_on_off_mode(void)
{
    gpio_init(LED_PIN);
    gpio_set_dir(LED_PIN, GPIO_OUT);
}

/** IRQ for the PWM which handles heartbeat mode. */
static void heartbeat_on_pwm_wrap_cb(void)
{
    static volatile int fade = 0;
    static volatile bool going_up = true;

    // Clear the interrupt flag that brought us here
    pwm_clear_irq(pwm_gpio_to_slice_num(LED_PIN));

    if (going_up)
    {
        fade++;
        if (fade > 255)
        {
            fade = 255;
            going_up = false;
        }
    }
    else
    {
        fade--;
        if (fade < 0)
        {
            fade = 0;
            going_up = true;
        }
    }
    // Square the fade value to make the LED's brightness appear more linear
    // Note this range matches with the wrap value
    pwm_set_gpio_level(LED_PIN, fade * fade);
}

/** Configure the LED pin for heartbeat mode. */
static void configure_led_heartbeat_mode(void)
{
    // This function is taken originally from the Pico examples

    // Tell the LED pin that the PWM is in charge of its value.
    gpio_set_function(LED_PIN, GPIO_FUNC_PWM);

    // Figure out which slice we just connected to the LED pin
    uint slice_num = pwm_gpio_to_slice_num(LED_PIN);

    // Register our interrupt handler with the PWM subsystem.
    pwm_clear_irq(slice_num);
    pwm_set_irq_enabled(slice_num, true);
    irq_set_exclusive_handler(PWM_IRQ_WRAP, heartbeat_on_pwm_wrap_cb);
    irq_set_enabled(PWM_IRQ_WRAP, true);

    // Get some sensible defaults for the slice configuration. By default, the
    // counter is allowed to wrap over its maximum range (0 to 2**16-1)
    pwm_config config = pwm_get_default_config();
    // Set divider, reduces counter clock to sysclock/this value
    pwm_config_set_clkdiv(&config, 4.0f);
    // Load the configuration into our PWM slice, and set it running.
    pwm_init(slice_num, &config, true);
}

/** Configure the LED mode. */
static void configure_led(led_mode_t new_mode)
{
    if (new_mode == led_mode)
    {
        log_debug("New LED mode is the same as the old one. Ignoring request to change.\n");
        return;
    }

    // Deconfigure old mode
    switch (led_mode)
    {
        case LED_MODE_ON_OFF:
            deconfigure_led_on_off_mode();
            break;
        case LED_MODE_HEARTBEAT:
            deconfigure_led_heartbeat_mode();
            break;
        case LED_MODE_UNASSIGNED:
            // Nothing to do
            break;
        default:
            log_error("LED is in an invalid state somehow. Attempting to set to new state anyway.\n");
            break;
    }

    // Set the mode flag with the new value
    led_mode = new_mode;

    // Configure new mode
    switch (new_mode)
    {
        case LED_MODE_ON_OFF:
            configure_led_on_off_mode();
            break;
        case LED_MODE_HEARTBEAT:
            configure_led_heartbeat_mode();
            break;
        case LED_MODE_UNASSIGNED:
            log_error("Trying to set the LED back to unassigned state after initialization.\n");
            // Fall through
        default:
            {
                log_error("Invalid LED mode: %d\n", new_mode);
                set_errno(ERR_ID_LEDS_MODULE, EINVAL);
                led_mode = LED_MODE_HEARTBEAT;
                configure_led_heartbeat_mode();
            }
            break;
    }
}

static void leds_on(void)
{
    if (led_mode != LED_MODE_ON_OFF)
    {
        configure_led(LED_MODE_ON_OFF);
    }
    gpio_put(LED_PIN, 1);
}

static void leds_off(void)
{
    if (led_mode != LED_MODE_ON_OFF)
    {
        configure_led(LED_MODE_ON_OFF);
    }
    gpio_put(LED_PIN, 0);
}

static void leds_heartbeat(void)
{
    if (led_mode != LED_MODE_HEARTBEAT)
    {
        configure_led(LED_MODE_HEARTBEAT);
    }
}

void leds_init(void)
{
    log_info("Init LEDs\n");
    configure_led(LED_MODE_HEARTBEAT);
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
