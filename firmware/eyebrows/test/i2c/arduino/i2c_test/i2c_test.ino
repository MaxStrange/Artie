// Wire Master Writer
// by Nicholas Zambetti <http://www.zambetti.com>

// Demonstrates use of the Wire library
// Writes data to an I2C/TWI Peripheral device
// Refer to the "Wire Peripheral Receiver" example for use with this

// Created 29 March 2006

// This example code is in the public domain.
#include <Wire.h>

#define PICO_ADDRESS 0x17
#define I2C_BAUDRATE (100U * 1000U)
#define LED_PIN 12

void setup()
{
    // Set up LED
    pinMode(LED_PIN, OUTPUT);

    // Set up I2C
    Wire.begin();
    Wire.setClock(I2C_BAUDRATE);
}

void loop()
{
    digitalWrite(LED_PIN, HIGH);
    Wire.beginTransmission(PICO_ADDRESS); // transmit to device PICO_ADDRESS
    Wire.write(0x00);                     // Turn off LED
    Wire.endTransmission(true);          // stop transmitting

    delay(1000);                          // Wait one second

    digitalWrite(LED_PIN, LOW);
    Wire.beginTransmission(PICO_ADDRESS); // transmit to device PICO_ADDRESS
    Wire.write(0x01);                     // Turn on LED
    Wire.endTransmission(true);          // stop transmitting

    delay(1000);                          // Wait one second
}
