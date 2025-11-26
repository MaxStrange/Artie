/**
 * @file temp.h
 * @brief Temperature sensor module.
 */
#pragma once

#ifdef __cplusplus
extern "C" {
#endif

/** Temperature, pressure, humidity values. */
typedef struct {
    float pressure_pa;
    float temperature_c;
    float humidity_percent_rh;
} temp_sensor_values_t;

/**
 * @brief Initialize temperature module.
 */
void temp_init(void);

/**
 * @brief Read the given values from the sensor.
 */
void temp_read(temp_sensor_values_t *values);

#ifdef __cplusplus
}
#endif
