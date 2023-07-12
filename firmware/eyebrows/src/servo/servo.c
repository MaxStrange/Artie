// Stdlib includes
#include <stdint.h>
#include <stdio.h>
// SDK includes
#include "hardware/pwm.h"
#include "hardware/clocks.h"
#include "pico/time.h"
// Local includes
#include "servo.h"
#include "../cmds/cmds.h"
#include "../board/errors.h"
#include "../board/pinconfig.h"

/** Macro for converting ms to micro seconds. */
#define MS_TO_US(x) ((x) * 1000U)

/**
 * Period of the square wave should be a little more than the maximum HIGH pulse width.
 * For a typical servo (including the ones Artie uses), that's 2 ms. So let's use 3 ms period
 */
#define PWM_PERIOD_MS 3

/** Top of the PWM counter. */
static const uint16_t COUNT_TOP = 0xFFFFU;

/** The middle of the servo's range (nominally). */
#define NOMINAL_MIDDLE_PULSE_WIDTH_MS 1.5f

/** The far left of the servo's range (nominally) */
#define NOMINAL_FAR_LEFT 1.0f

/** The far right of the servo's range (nominally) */
#define NOMINAL_FAR_RIGHT 2.0f

/** Last known safe position left of center. */
static float last_known_safe_left = NOMINAL_FAR_LEFT;

/** Last known safe position right of center. */
static float last_known_safe_right = NOMINAL_FAR_RIGHT;

/** Are we calibrating the servo? */
static bool currently_calibrating = false;

/** Set the servo's PWM pin to a duty cycle such that the HIGH portion of the square wave is `ms` long. */
static void set_pulse_width(float ms)
{
    assert(ms >= NOMINAL_FAR_LEFT);
    assert(ms <= NOMINAL_FAR_RIGHT);

    // Set to duty cycle based on the frequency that we've already configured for
    float duty_cycle = ms / (float)PWM_PERIOD_MS;
    float count_fraction = (float)((uint32_t)COUNT_TOP + 1) * duty_cycle;
    assert(count_fraction >= 0);
    assert(count_fraction <= COUNT_TOP);
    pwm_set_gpio_level(SERVO_PWM_PIN, (uint16_t)count_fraction);
}

/** Default GPIO IRQ handler for the whole system. If we add more interrupts, we should use raw handlers instead. */
static void limit_switch_callback(uint gpio, uint32_t events)
{
    if (gpio == LIMIT_SWITCH_LEFT)
    {
        set_pulse_width(last_known_safe_left);
        currently_calibrating = false;
    }

    if (gpio == LIMIT_SWITCH_RIGHT)
    {
        set_pulse_width(last_known_safe_right);
        currently_calibrating = false;
    }
}

static void calibrate_servo(void)
{
    float prev_value = NOMINAL_MIDDLE_PULSE_WIDTH_MS;
    float next_value;

    // Run the servo all the way left to find where the limit is.
    currently_calibrating = true;
    uint32_t timestamp_ms = to_ms_since_boot(get_absolute_time());
    while (currently_calibrating)
    {
        // Determine next value
        next_value = prev_value - 0.1f;
        next_value = (next_value < NOMINAL_FAR_LEFT) ? NOMINAL_FAR_LEFT : next_value;

        // Set pulse width
        set_pulse_width(next_value);

        // Wait a bit for servo to drive to target
        busy_wait_us(MS_TO_US(50));

        // If we haven't tripped the limit switch, set prev_value to next_value
        if (currently_calibrating)
        {
            prev_value = next_value;
        }

        // If we have been doing this for too long, cancel calibration.
        // We have a potential hardware misconfiguration. Let someone know.
        if ((to_ms_since_boot(get_absolute_time()) - timestamp_ms) >= 2000U)
        {
            set_errno(ERR_ID_SERVO_MODULE, ETIME);
            log_warning("Calibration timed out. Potentially misconfigured servo encasing.\n");
            return;
        }
    }
    last_known_safe_left = prev_value;

    // Drive to center
    set_pulse_width(NOMINAL_MIDDLE_PULSE_WIDTH_MS);
    busy_wait_us(MS_TO_US(50));

    // Repeat on the right
    prev_value = NOMINAL_MIDDLE_PULSE_WIDTH_MS;
    currently_calibrating = true;
    timestamp_ms = to_ms_since_boot(get_absolute_time());
    while (currently_calibrating)
    {
        // Determine next value
        next_value = prev_value + 0.1f;
        next_value = (next_value > NOMINAL_FAR_RIGHT) ? NOMINAL_FAR_RIGHT : next_value;

        // Set pulse width
        set_pulse_width(next_value);

        // Wait a bit for servo to drive to target
        busy_wait_us(MS_TO_US(50));

        // If we haven't tripped the limit switch, set prev_value to next_value
        if (currently_calibrating)
        {
            prev_value = next_value;
        }

        // If we have been doing this for too long, cancel calibration.
        // We have a potential hardware misconfiguration. Let someone know.
        if ((to_ms_since_boot(get_absolute_time()) - timestamp_ms) >= 2000U)
        {
            set_errno(ERR_ID_SERVO_MODULE, ETIME);
            log_warning("Calibration timed out. Potentially misconfigured servo encasing.\n");
            return;
        }
    }
    last_known_safe_right = prev_value;
}

void servo_init(void)
{
    log_info("Init servo\n");

    // Initialize limit switch left with interrupt (active low)
    // First pin is used to enable interrupts for GPIO and to add a default handler for all pins.
    gpio_set_irq_enabled_with_callback(LIMIT_SWITCH_LEFT, GPIO_IRQ_EDGE_FALL, true, &limit_switch_callback);

    // Initialize limit switch right with interrupt (active low)
    // Additional pin interrupts are enabled like this.
    gpio_set_irq_enabled(LIMIT_SWITCH_RIGHT, GPIO_IRQ_EDGE_FALL, true);

    // Clock division calculation for the PWM counter
    // We want PWM_PERIOD_MS for our period (in ms)
    float sysclock_frequency_hz = (float)clock_get_hz(clk_sys);
    float default_timer_period_ms = ((float)COUNT_TOP / sysclock_frequency_hz) * (1000.0f); // multiply by a thousand to get ms
    float division = (float)PWM_PERIOD_MS / default_timer_period_ms;

    // Initialize servo pin for PWM. Configure PWM to count to count_top in PWM_PERIOD_MS ms.
    gpio_set_function(SERVO_PWM_PIN, GPIO_FUNC_PWM);
    uint slice_num = pwm_gpio_to_slice_num(SERVO_PWM_PIN);
    pwm_config cfg = pwm_get_default_config();
    pwm_config_set_wrap(&cfg, COUNT_TOP);
    pwm_config_set_clkdiv(&cfg, division);

    // Start the PWM signal
    pwm_init(slice_num, &cfg, true);

    // Run the calibration procedure
    calibrate_servo();
}

void servo_cmd(cmd_t command)
{
    // Servo commands are always "turn"
    // The first two bits are the subsystem mask.
    // The 6 LSbs are mapped into the usable range of degrees for the eyeball enclosure.
    uint8_t servo_cmd_param = command & 0x3F;

    // Six bits means range [0, 63]
    // 0  => 0 deg      (1.0 ms)
    // 31 => 90 deg     (1.5 ms)
    // 63 => 180 deg    (2.0 ms)
    // Use a function that maps from the range [0, 63] to [1.0, 2.0]
    // with a sharp fall off towards the less useful ends of the range
    // so that the bits are used most efficiently.
    // y = (1/65,000) * (x - 31)^3 + 1.5
    // NOTE: There is no hard floating point in the Pico.
    //       This likely takes an egregious amount of time.
    static const float scaling_factor = 1.5384e-05f;                // 1/65,000 ish
    static const float x_offset = -31.0f;                           // Slide the graph to center on halfway between 0 and 63
    static const float y_offset = NOMINAL_MIDDLE_PULSE_WIDTH_MS;    // Shift up so that the 31 falls on 1.5 ms (nominally)
    float x = (float)servo_cmd_param;
    float pulse_width_ms = scaling_factor * ((x + x_offset) * (x + x_offset) * (x + x_offset)) + y_offset;

    // Make sure to bound the result
    pulse_width_ms = (pulse_width_ms < last_known_safe_left)  ? last_known_safe_left : pulse_width_ms;
    pulse_width_ms = (pulse_width_ms > last_known_safe_right) ? last_known_safe_right : pulse_width_ms;

    // Set duty cycle on PWM line
    set_pulse_width(pulse_width_ms);
}
