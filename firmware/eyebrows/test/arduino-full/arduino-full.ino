#include <Wire.h>

#define PICO_ADDRESS 0x17
#define I2C_BAUDRATE (100U * 1000U)
#define LED_PIN 12

#define CMD_MODULE_ID_LEDS  0x00
#define CMD_MODULE_ID_LCD   0x40
#define CMD_MODULE_ID_SERVO 0x80

#define MSG_DELAY_MS 2500

/**
 * @brief The types of commands we can receive and act on.
 *
 */
typedef enum {
    CMD_LED_ON          = (CMD_MODULE_ID_LEDS   | 0x00),
    CMD_LED_OFF         = (CMD_MODULE_ID_LEDS   | 0x01),
    CMD_LED_HEARTBEAT   = (CMD_MODULE_ID_LEDS   | 0x02),
    CMD_LCD_TEST        = (CMD_MODULE_ID_LCD    | 0x11),
    CMD_LCD_OFF         = (CMD_MODULE_ID_LCD    | 0x22)
} cmd_t;

void setup()
{
    // Set up LED
    pinMode(LED_PIN, OUTPUT);

    // Set up I2C
    Wire.begin();
    Wire.setClock(I2C_BAUDRATE);
}

static void control(uint8_t cmd)
{
    Wire.beginTransmission(PICO_ADDRESS);
    Wire.write(cmd);
    Wire.endTransmission(true);
}

static void write_surprised_eyebrow(void)
{
    // ---
    //
    //
    uint8_t surprised = 0x07;
    control(CMD_MODULE_ID_LCD | surprised);
}

static void write_angry_eyebrow(void)
{
    //
    // --
    //   -
    uint8_t angry = 0x30;//0bxx11 0000
    control(CMD_MODULE_ID_LCD | angry);
}

static void write_sad_eyebrow(void)
{
    //   -
    //  -
    // -
    uint8_t sad = 0x11;//0bxx01 0001
    control(CMD_MODULE_ID_LCD | sad);
}

static void write_neutral_eyebrow(void)
{
    //
    // ---
    //
    uint8_t neutral = 0x38;//0bxx11 1000
    control(CMD_MODULE_ID_LCD | neutral);
}

static void write_skeptical_eyebrow(void)
{
    //
    //
    // ---
    uint8_t skeptical = 0x00;//0bxx00 0000
    control(CMD_MODULE_ID_LCD | skeptical);
}

static void write_happy_eyebrow(void)
{
    //  -
    // - -
    //
    uint8_t happy = 0x2A;//0bxx10 1010
    control(CMD_MODULE_ID_LCD | happy);
}

static void write_smiling_eyebrow(void)
{
    //  --
    // -
    //
    uint8_t smiling = 0x23;//0bxx10 0011
    control(CMD_MODULE_ID_LCD | smiling);
}

void loop()
{
    digitalWrite(LED_PIN, HIGH);
    control(CMD_LED_ON);
    delay(MSG_DELAY_MS);
    control(CMD_LED_OFF);
    delay(MSG_DELAY_MS);
    control(CMD_LCD_TEST);
    delay(MSG_DELAY_MS);

    digitalWrite(LED_PIN, LOW);
    control(CMD_LED_ON);
    delay(MSG_DELAY_MS);
    control(CMD_LED_OFF);
    delay(MSG_DELAY_MS);
    control(CMD_LCD_OFF);
    delay(MSG_DELAY_MS);

    digitalWrite(LED_PIN, LOW);
    control(CMD_LED_ON);
    delay(MSG_DELAY_MS);
    control(CMD_LED_OFF);
    delay(MSG_DELAY_MS);
    write_angry_eyebrow();
    delay(MSG_DELAY_MS);

    digitalWrite(LED_PIN, LOW);
    control(CMD_LED_ON);
    delay(MSG_DELAY_MS);
    control(CMD_LED_OFF);
    delay(MSG_DELAY_MS);
    write_smiling_eyebrow();
    delay(MSG_DELAY_MS);

    digitalWrite(LED_PIN, LOW);
    control(CMD_LED_ON);
    delay(MSG_DELAY_MS);
    control(CMD_LED_OFF);
    delay(MSG_DELAY_MS);
    write_skeptical_eyebrow();
    delay(MSG_DELAY_MS);

    digitalWrite(LED_PIN, LOW);
    control(CMD_LED_ON);
    delay(MSG_DELAY_MS);
    control(CMD_LED_OFF);
    delay(MSG_DELAY_MS);
    write_sad_eyebrow();
    delay(MSG_DELAY_MS);

    digitalWrite(LED_PIN, LOW);
    control(CMD_LED_ON);
    delay(MSG_DELAY_MS);
    control(CMD_LED_OFF);
    delay(MSG_DELAY_MS);
    write_neutral_eyebrow();
    delay(MSG_DELAY_MS);

    digitalWrite(LED_PIN, LOW);
    control(CMD_LED_ON);
    delay(MSG_DELAY_MS);
    control(CMD_LED_OFF);
    delay(MSG_DELAY_MS);
    write_happy_eyebrow();
    delay(MSG_DELAY_MS);

    digitalWrite(LED_PIN, LOW);
    control(CMD_LED_ON);
    delay(MSG_DELAY_MS);
    control(CMD_LED_OFF);
    delay(MSG_DELAY_MS);
    write_surprised_eyebrow();
    delay(MSG_DELAY_MS);
}
