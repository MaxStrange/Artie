// Stdlib includes
#include <stdbool.h>
// SDK includes
#include "hardware/spi.h"
// Local includes
#include "../cmds/cmds.h"
#include "../board/errors.h"
#include "imu.h"
#include "sensors.h"
#include "temp.h"

/** The ms between each read of the sensors. */
#define MS_BETWEEN_SENSOR_READ 1000U

/** Set to true whenever we are in the sensor-reading ISR. */
volatile static bool setting_sensor_values = false; // TODO: Upgrade to true mutex

/** Sensor values are assigned during the ISR. */
volatile static sensor_values_t sensor_values = {
    .temp_sensor_values = {
        .pressure_pa = 0.0f,
        .temperature_c = 0.0f,
        .humidity_percent_rh = 0.0f,
    },
    .imu_sensor_values = {
        .gyro_x = 0,
        .gyro_y = 0,
        .gyro_z = 0,
        .accel_x = 0,
        .accel_y = 0,
        .accel_z = 0,
    }
};

/** Wrapper around cmds_set_register_value to make sure we are abiding by the mutex. */
static inline void set_register_value(const float *val)
{
    // Spinlock while we wait for the flag to clear.
    while (setting_sensor_values)
    {
        sleep_ns(100);
    }

    setting_sensor_values = true;
    cmds_set_register_value(*val);
    setting_sensor_values = false;
}

/** The callback we use every so often from the timer. */
static bool sensor_read_cb(repeating_timer_t *unused)
{
    // Read temperature, pressure, humidity
    temp_sensor_values_t temp_temp_vals;
    temp_read(&temp_temp_vals);

    // Read 6DOF IMU values
    imu_sensor_values_t temp_imu_vals;
    imu_read(&temp_imu_vals);

    // Transfer shadow values
    setting_sensor_values = true;
    sensor_values.imu_sensor_values = temp_imu_vals;
    sensor_values.temp_sensor_values = temp_temp_vals;
    setting_sensor_values = false;  // sensor values are safe to read now
    // Always return true (false stops the alarm, true fires it off again)
    return true;
}

void sensors_init(void)
{
    // Initialize the SPI interface that the sensors will be using
    spi_init(spi_default, 500 * 1000); // 500 kHz
    gpio_set_function(SENSORS_SPI_MISO, GPIO_FUNC_SPI);
    gpio_set_function(SENSORS_SPI_CLOCK, GPIO_FUNC_SPI);
    gpio_set_function(SENSORS_SPI_MOSI, GPIO_FUNC_SPI);

    // Initialize the sensors themselves
    temp_init();
    imu_init();

    // Initialize a timer with callbacks for reading temperature/pressure/humidity and IMU values.
    bool worked = add_repeating_timer_ms(MS_BETWEEN_SENSOR_READ, &sensor_read_cb, NULL, NULL);
    if (!worked)
    {
        log_error("Could not initialize repeating sensor read timer.\n");
    }
}

void sensors_cmd(cmd_t command)
{
    switch (command)
    {
        case CMD_SENSORS_READ_TEMPERATURE:
            set_register_value(&sensor_values.temp_sensor_values.temperature_c);
            break;
        case CMD_SENSORS_READ_HUMIDITY:
            set_register_value(&sensor_values.temp_sensor_values.humidity_percent_rh);
            break;
        case CMD_SENSORS_READ_PRESSURE:
            set_register_value(&sensor_values.temp_sensor_values.pressure_pa);
            break;
        case CMD_SENSORS_READ_ACCEL_X:
            set_register_values((float *)&sensor_values.imu_sensor_values.accel_x);
            break;
        case CMD_SENSORS_READ_ACCEL_Y:
            set_register_values((float *)&sensor_values.imu_sensor_values.accel_y);
            break;
        case CMD_SENSORS_READ_ACCEL_Z:
            set_register_values((float *)&sensor_values.imu_sensor_values.accel_z);
            break;
        case CMD_SENSORS_READ_GYRO_X:
            set_register_values((float *)&sensor_values.imu_sensor_values.gyro_x);
            break;
        case CMD_SENSORS_READ_GYRO_Y:
            set_register_values((float *)&sensor_values.imu_sensor_values.gyro_y);
            break;
        case CMD_SENSORS_READ_GYRO_Z:
            set_register_values((float *)&sensor_values.imu_sensor_values.gyro_z);
            break;
        default:
            log_error("Illegal cmd type 0x%02X\n in sensors subsystem", command);
            break;
    }
}
