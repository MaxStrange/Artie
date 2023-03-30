// The compenstation code in this module is taken from the bme280_spi example in the pico examples.

// Stdlib includes
// SDK includes
#include "pico/stdlib.h"
// Local includes
#include "../board/errors.h"
#include "../board/pinconfig.h"
#include "spi_interface.h"
#include "temp.h"

/** Register definitions */
#define BME280_REG_ID 0xD0
#define BME280_REG_RESET 0xE0
#define BME280_REG_CTRL_HUM 0xF2
#define BME280_REG_STATUS 0xF3
#define BME280_REG_CTRL_MEAS 0xF4
#define BME280_REG_CONFIG 0xF5
#define BME280_REG_PRESS 0xF7  // And F8 and F9 for (msb, lsb, xlsb)
#define BME280_REG_TEMP 0xFA   // And FB and FC for (msb, lsb, xlsb)
#define BME280_REG_HUM 0xFD    // And FE for (msb, lsb)

/** Compensation values struct definition. */
typedef struct {
    int32_t t_fine;
    uint16_t dig_T1;
    int16_t dig_T2;
    int16_t dig_T3;
    uint16_t dig_P1;
    int16_t dig_P2;
    int16_t dig_P3;
    int16_t dig_P4;
    int16_t dig_P5;
    int16_t dig_P6;
    int16_t dig_P7;
    int16_t dig_P8;
    int16_t dig_P9;
    int16_t dig_H2;
    int16_t dig_H4;
    int16_t dig_H5;
    uint8_t dig_H1;
    uint8_t dig_H3;
    int8_t dig_H6;
} comp_vals_t;

/** Store the compensation values in a struct. */
static comp_vals_t compensation_values = {};

/** CS pull down with a few no-ops to ensure compatability with the sensor's timing. */
static inline void cs_select() {
    asm volatile("nop \n nop \n nop");
    gpio_put(SENSORS_SPI_CS_TEMP, 0);
    asm volatile("nop \n nop \n nop");
}

/** CS pull up with a few no-ops to ensure compatability with the sensor's timing. */
static inline void cs_deselect() {
    asm volatile("nop \n nop \n nop");
    gpio_put(PICO_DEFAULT_SPI_CSN_PIN, 1);
    asm volatile("nop \n nop \n nop");
}

/** Simple blocking read. Suitable to be run from an interrupt context if necessary. */
static volatile void blocking_read(uint8_t reg, uint8_t *buf, uint16_t len)
{
    // BME280 requires the most significant bit to be 1 to signal a read. 0 signals a write.
    reg |= (1 << 7);
    myspi_blocking_read(SENSORS_SPI_CS_TEMP, reg, buf, len);
}

/** Simple blocking write. */
static void blocking_write(uint8_t reg, uint8_t byte)
{
    // Clear the msb to show that we are writing.
    reg &= ~(1 << 7);
    myspi_blocking_write(SENSORS_SPI_CS_TEMP, reg, byte);
}

/** Trigger a soft reset the temperature sensor. */
static void reset_sensor(void)
{
    // Magic value required to reset the chip according to the datasheet.
    uint8_t reg = BME280_REG_RESET;
    uint8_t magic_value = 0xB6;
    blocking_write(reg, magic_value);
}

/**
 * @brief Adjust the raw ADC value for temperature into usable temperature value based on calibration values.
 *
 * Beware that this must be called BEFORE the other compensation functions, as it adjusts the value
 * of t_fine.
 *
 * Returns T in degrees C.
 */
static float compensate_temp(int32_t adc_T)
{
    int32_t var1;
    int32_t var2;
    int32_t T;
    var1 = ((((adc_T >> 3) - ((int32_t) compensation_values.dig_T1 << 1))) * ((int32_t) compensation_values.dig_T2)) >> 11;
    var2 = (((((adc_T >> 4) - ((int32_t) compensation_values.dig_T1)) * ((adc_T >> 4) - ((int32_t) compensation_values.dig_T1))) >> 12) * ((int32_t) compensation_values.dig_T3))
            >> 14;

    compensation_values.t_fine = var1 + var2;
    T = (compensation_values.t_fine * 5 + 128) >> 8;

    // Convert to degrees C
    T = T / 100.0f;

    return T;
}

/** Adjust the raw ADC value for pressure into usable pressure value based on calibration values. Returns Pa. */
static float compensate_pressure(int32_t adc_P)
{
    int32_t var1;
    int32_t var2;
    uint32_t p;
    var1 = (((int32_t) compensation_values.t_fine) >> 1) - (int32_t) 64000;
    var2 = (((var1 >> 2) * (var1 >> 2)) >> 11) * ((int32_t) compensation_values.dig_P6);
    var2 = var2 + ((var1 * ((int32_t) compensation_values.dig_P5)) << 1);
    var2 = (var2 >> 2) + (((int32_t) compensation_values.dig_P4) << 16);
    var1 = (((compensation_values.dig_P3 * (((var1 >> 2) * (var1 >> 2)) >> 13)) >> 3) + ((((int32_t) compensation_values.dig_P2) * var1) >> 1)) >> 18;
    var1 = ((((32768 + var1)) * ((int32_t) compensation_values.dig_P1)) >> 15);
    if (var1 == 0)
        return 0;

    p = (((uint32_t) (((int32_t) 1048576) - adc_P) - (var2 >> 12))) * 3125;
    if (p < 0x80000000)
        p = (p << 1) / ((uint32_t) var1);
    else
        p = (p / (uint32_t) var1) * 2;

    var1 = (((int32_t) compensation_values.dig_P9) * ((int32_t) (((p >> 3) * (p >> 3)) >> 13))) >> 12;
    var2 = (((int32_t) (p >> 2)) * ((int32_t) compensation_values.dig_P8)) >> 13;
    p = (uint32_t) ((int32_t) p + ((var1 + var2 + compensation_values.dig_P7) >> 4));

    // Convert to Pa
    p = p / 256.0f;

    return p;
}

/** Adjust the raw ADC value for humidity into usable humidity value based on calibration values. Return %RH. */
static uint32_t compensate_humidity(int32_t adc_H)
{
    int32_t v_x1_u32r;
    v_x1_u32r = (compensation_values.t_fine - ((int32_t) 76800));
    v_x1_u32r = (((((adc_H << 14) - (((int32_t) compensation_values.dig_H4) << 20) - (((int32_t) compensation_values.dig_H5) * v_x1_u32r)) +
                   ((int32_t) 16384)) >> 15) * (((((((v_x1_u32r * ((int32_t) compensation_values.dig_H6)) >> 10) * (((v_x1_u32r * ((int32_t) compensation_values.dig_H3))
            >> 11) + ((int32_t) 32768))) >> 10) + ((int32_t) 2097152)) * ((int32_t) compensation_values.dig_H2) + 8192) >> 14));
    v_x1_u32r = (v_x1_u32r - (((((v_x1_u32r >> 15) * (v_x1_u32r >> 15)) >> 7) * ((int32_t) compensation_values.dig_H1)) >> 4));
    v_x1_u32r = (v_x1_u32r < 0 ? 0 : v_x1_u32r);
    v_x1_u32r = (v_x1_u32r > 419430400 ? 419430400 : v_x1_u32r);

    // Convert to % relative humidity
    float humidity = (uint32_t)(v_x1_u32r >> 12);
    humidity = humidity / 1024.0f;

    return humidity;
}

/** This function reads the manufacturing assigned compensation parameters from the device */
static void read_compensation_parameters()
{
    uint8_t buffer[26];

    blocking_read(0x88, buffer, 24);

    compensation_values.dig_T1 = buffer[0] | (buffer[1] << 8);
    compensation_values.dig_T2 = buffer[2] | (buffer[3] << 8);
    compensation_values.dig_T3 = buffer[4] | (buffer[5] << 8);

    compensation_values.dig_P1 = buffer[6] | (buffer[7] << 8);
    compensation_values.dig_P2 = buffer[8] | (buffer[9] << 8);
    compensation_values.dig_P3 = buffer[10] | (buffer[11] << 8);
    compensation_values.dig_P4 = buffer[12] | (buffer[13] << 8);
    compensation_values.dig_P5 = buffer[14] | (buffer[15] << 8);
    compensation_values.dig_P6 = buffer[16] | (buffer[17] << 8);
    compensation_values.dig_P7 = buffer[18] | (buffer[19] << 8);
    compensation_values.dig_P8 = buffer[20] | (buffer[21] << 8);
    compensation_values.dig_P9 = buffer[22] | (buffer[23] << 8);

    compensation_values.dig_H1 = buffer[25];

    blocking_read(0xE1, buffer, 8);

    compensation_values.dig_H2 = buffer[0] | (buffer[1] << 8);
    compensation_values.dig_H3 = (int8_t) buffer[2];
    compensation_values.dig_H4 = buffer[3] << 4 | (buffer[4] & 0xf);
    compensation_values.dig_H5 = (buffer[5] >> 4) | (buffer[6] << 4);
    compensation_values.dig_H6 = (int8_t) buffer[7];
}

void temp_init(void)
{
    // Chip select is active LOW, so initialize as HIGH
    gpio_init(SENSORS_SPI_CS_TEMP);
    gpio_set_dir(SENSORS_SPI_CS_TEMP, GPIO_OUT);
    gpio_put(SENSORS_SPI_CS_TEMP, 1);

    // Sanity check that we can read a value from the chip (read the ID)
    uint8_t id;
    blocking_read(BME280_REG_ID, &id, sizeof(id));
    if (id != 0x60)
    {
        log_error("BME280 temperature sensor reads id 0x%x, but should be 0x60.\n");
    }

    // Reset the sensor
    reset_sensor();

    // Oversampling settings: 1x 1x 1x (pressure, temp, humidity)
    blocking_write(BME280_REG_CTRL_HUM, 0x01);

    // Set IIR Filter to OFF
    blocking_write(BME280_REG_CONFIG, 0x00);  // bxxx0 0000 -> (don't care about t_standby) (no IIR) (SPI 4 wire mode)

    // Read compensation values
    read_compensation_parameters();

    // Set mode to Forced (sleep mode is default after power on)
    // Forced mode means the sensor will sleep unless we specifically request a measurement.
    // Also set the rest of the oversampling settings
    blocking_write(BME280_REG_CTRL_MEAS, 0x25);  // b0010 0100 -> x1 x1 forced mode
}

void temp_read(temp_sensor_values_t *values)
{
    // Non-blocking read of all values
    static uint8_t buffer[8];
    blocking_read(BME280_REG_PRESS, buffer, 8);
    int32_t adc_pressure = ((uint32_t) buffer[0] << 12) | ((uint32_t) buffer[1] << 4) | (buffer[2] >> 4);
    int32_t adc_temp = ((uint32_t) buffer[3] << 12) | ((uint32_t) buffer[4] << 4) | (buffer[5] >> 4);
    int32_t adc_humidity = (uint32_t) buffer[6] << 8 | buffer[7];

    // Compensate using calibrated parameters
    values->temperature_c = compensate_temp(adc_temp);
    values->pressure_pa = compensate_pressure(adc_pressure);
    values->humidity_percent_rh =compensate_humidity(adc_humidity);
}
