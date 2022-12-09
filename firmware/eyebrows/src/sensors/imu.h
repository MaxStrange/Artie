/**
 * @file imu.h
 * @brief Module for the accelerator/gyroscope.
 */
#pragma once

#ifdef __cplusplus
extern "C" {
#endif

/** 6DOF IMU values. The order of these values matches the order found in the device. Do not change. */
typedef struct {
    int16_t gyro_x;
    int16_t gyro_y;
    int16_t gyro_z;
    int16_t accel_x;
    int16_t accel_y;
    int16_t accel_z;
} imu_sensor_values_t;

/**
 * @brief Initialize the IMU module.
 */
void imu_init(void);

/** Read the IMU values into the given pointer. */
void imu_read(imu_sensor_values_t *values);

#ifdef __cplusplus
}
#endif
