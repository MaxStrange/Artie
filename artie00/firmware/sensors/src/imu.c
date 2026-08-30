// Stdlib includes
// SDK includes
#include <pico/stdlib.h>
// Local includes
#include "../board/errors.h"
#include "../board/pinconfig.h"
#include "imu.h"
#include "spi_interface.h"

/** LSM6DSO register addresses */
#define LSM_REG_FUNC_CFG_ACCESS             0x01
#define LSM_REG_PIN_CTRL                    0x02
#define LSM_REG_FIFO_CTRL1                  0x07
#define LSM_REG_FIFO_CTRL2                  0x08
#define LSM_REG_FIFO_CTRL3                  0x09
#define LSM_REG_FIFO_CTRL4                  0x0A
#define LSM_REG_COUNTER_BDR_REG1            0x0B
#define LSM_REG_COUNTER_BDR_REG2            0x0C
#define LSM_REG_INT1_CTRL                   0x0D
#define LSM_REG_INT2_CTRL                   0x0E
#define LSM_REG_WHO_AM_I                    0x0F
#define LSM_REG_CTRL1_XL                    0x10
#define LSM_REG_CTRL2_G                     0x11
#define LSM_REG_CTRL3_C                     0x12
#define LSM_REG_CTRL4_C                     0x13
#define LSM_REG_CTRL5_C                     0x14
#define LSM_REG_CTRL6_C                     0x15
#define LSM_REG_CTRL7_G                     0x16
#define LSM_REG_CTRL8_XL                    0x17
#define LSM_REG_CTRL9_XL                    0x18
#define LSM_REG_CTRL10_C                    0x19
#define LSM_REG_ALL_INT_SRC                 0x1A
#define LSM_REG_WAKE_UP_SRC                 0x1B
#define LSM_REG_TAP_SRC                     0x1C
#define LSM_REG_D6D_SRC                     0x1D
#define LSM_REG_STATUS_REG                  0x1E
#define LSM_REG_OUT_TEMP_L                  0x20
#define LSM_REG_OUT_TEMP_H                  0x21
#define LSM_REG_OUTX_L_G                    0x22
#define LSM_REG_OUTX_H_G                    0x23
#define LSM_REG_OUTY_L_G                    0x24
#define LSM_REG_OUTY_H_G                    0x25
#define LSM_REG_OUTZ_L_G                    0x26
#define LSM_REG_OUTZ_H_G                    0x27
#define LSM_REG_OUTX_L_A                    0x28
#define LSM_REG_OUTX_H_A                    0x29
#define LSM_REG_OUTY_L_A                    0x2A
#define LSM_REG_OUTY_H_A                    0x2B
#define LSM_REG_OUTZ_L_A                    0x2C
#define LSM_REG_OUTZ_H_A                    0x2D
#define LSM_REG_EMB_FUNC_STATUS_MAINPAGE    0x35
#define LSM_REG_FSM_STATUS_A_MAINPAGE       0x36
#define LSM_REG_FSM_STATUS_B_MAINPAGE       0x37
#define LSM_REG_STATUS_MASTER_MAINPAGE      0x39
#define LSM_REG_FIFO_STATUS1                0x3A
#define LSM_REG_FIFO_STATUS2                0x3B
#define LSM_REG_TIMESTAMP0                  0x40
#define LSM_REG_TIMESTAMP1                  0x41
#define LSM_REG_TIMESTAMP2                  0x42
#define LSM_REG_TIMESTAMP3                  0x43
#define LSM_REG_TAP_CFG0                    0x56
#define LSM_REG_TAP_CFG1                    0x57
#define LSM_REG_TAP_CFG2                    0x58
#define LSM_REG_TAP_THS_6D                  0x59
#define LSM_REG_INT_DUR2                    0x5A
#define LSM_REG_WAKE_UP_THS                 0x5B
#define LSM_REG_WAKE_UP_DUR                 0x5C
#define LSM_REG_FREE_FALL                   0x5D
#define LSM_REG_MD1_CFG                     0x5E
#define LSM_REG_MD2_CFG                     0x5F
#define LSM_REG_i3C_BUS_AVB                 0x62
#define LSM_REG_INTERNAL_FREQ_FINE          0x63
#define LSM_REG_INT_OIS                     0x6F
#define LSM_REG_CTRL1_OIS                   0x70
#define LSM_REG_CTRL2_OIS                   0x71
#define LSM_REG_CTRL3_OIS                   0x72
#define LSM_REG_X_OFS_USR                   0x73
#define LSM_REG_Y_OFS_USR                   0x74
#define LSM_REG_Z_OFS_USR                   0x75
#define LSM_REG_FIFO_DATA_OUT_TAG           0x78
#define LSM_REG_FIFO_DATA_OUT_X_L           0x79
#define LSM_REG_FIFO_DATA_OUT_X_H           0x7A
#define LSM_REG_FIFO_DATA_OUT_Y_L           0x7B
#define LSM_REG_FIFO_DATA_OUT_Y_H           0x7C
#define LSM_REG_FIFO_DATA_OUT_Z_L           0x7D
#define LSM_REG_FIFO_DATA_OUT_Z_H           0x7E

static inline void blocking_write(uint8_t reg, uint8_t byte)
{
    myspi_blocking_write(SENSORS_SPI_CS_IMU, reg, byte);
}

static inline void blocking_read(uint8_t reg, uint8_t *buf, uint16_t len)
{
    myspi_blocking_read(SENSORS_SPI_CS_IMU, reg, buf, len);
}

void imu_read(imu_sensor_values_t *values)
{
    blocking_read(LSM_REG_OUTX_L_G, (uint8_t *)values, sizeof(imu_sensor_values_t));
}

void imu_init(void)
{
    // Chip select is active-low, so initialize as HIGH
    gpio_init(SENSORS_SPI_CS_IMU);
    gpio_set_dir(SENSORS_SPI_CS_IMU, GPIO_OUT);
    gpio_put(SENSORS_SPI_CS_IMU, 1);

    // Sanity check that we can read a value from the chip (read the ID)
    uint8_t id;
    blocking_read(LSM_REG_WHO_AM_I, &id, sizeof(id));
    if (id != 0x6C)
    {
        log_error("LSM IMU reads id 0x%x, but should be 0x6C.\n");
    }

    // Reset the sensor
    blocking_write(LSM_REG_CTRL3_C, 0x85);
    sleep_ms(5);

    // Disable compression
    blocking_write(LSM_REG_FIFO_CTRL2, 0x00);
    // Disable FIFO
    blocking_write(LSM_REG_FIFO_CTRL4, 0x00);
    // Set up the accelerometer - 208Hz (normal mode), 8g range, enable second LPF
    blocking_write(LSM_REG_CTRL1_XL, 0x5E);
    // Set up the gyroscope - 208Hz (normal mode), 500 degrees per second range
    blocking_write(LSM_REG_CTRL2_G, 0x54);
    // Don't signal data ready until filter settling ends, disable i2c, enable gyro LPF1
    blocking_write(LSM_REG_CTRL4_C, 0x0E);
    // Gyroscope LPF1 bandwidth selection = 12.2
    blocking_write(LSM_REG_CTRL6_C, 0x07);
    // Accelerometer bandwith selection = ODR/20 (208Hz/20 = 10.4)
    blocking_write(LSM_REG_CTRL8_XL, 0x41);
    // Disable data-enable bits being embedded into the sensor values, disable I3C interface
    blocking_write(LSM_REG_CTRL9_XL, 0x02);
}
