/**
 * @file sensors.h
 * @brief Interface to the sensors submodule.
 * The rest of the program should talk to this module instead
 * of talking to the other sensors directly.
 *
 */
#pragma once

#ifdef __cplusplus
extern "C" {
#endif

#include "../cmds/cmds.h"
#include "imu.h"
#include "temp.h"

/** Sensor values all together. */
typedef struct {
    temp_sensor_values_t temp_sensor_values;
    imu_sensor_values_t imu_sensor_values;
} sensor_values_t;

/**
 * @brief Initialize the sensors subsystem.
 * This will initialize a timer that periodically fires off
 * a callback which utilizes the SPI bus to communicate with the
 * sensors.
 */
void sensors_init(void);

/** Execute the given command. */
void sensors_cmd(cmd_t command);

#ifdef __cplusplus
}
#endif
