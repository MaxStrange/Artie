"""
This is the board config for the controller node.
"""
# UART
## No custom software depends on this, so double check in the current schematic when referencing
UART_TX = 14  # GPIO 14 (BCM mode -> physical pin 8)
UART_RX = 15  # GPIO 15 (BCM mode -> physical pin 10)
UART_CTS = 16 # GPIO 16 (BCM mode -> physical pin 36)
UART_CTS = 17 # GPIO 17 (BCM mode -> physical pin 11)

# LED Pin
LED_PIN = 18  # GPIO 18 (BCM mode -> physical pin 12, at least on RPi 4B)

# SWD
## Mouth
SWDIO_MOUTH = 22  # GPIO 22 (BCM mode -> physical pin 15)
SWCLK_MOUTH = 23  # GPIO 23 (BCM mode -> physical pin 16)
## Left Eyebrow
SWDIO_EYEBROW_LEFT = 24  # GPIO 24 (BCM mode -> physical pin 18)
SWCLK_EYEBROW_LEFT = 25  # GPIO 25 (BCM mode -> physical pin 22)
## Right Eyebrow
SWDIO_EYEBROW_RIGHT = 5  # GPIO  5 (BCM mode -> physical pin 29)
SWCLK_EYEBROW_RIGHT = 6  # GPIO  6 (BCM mode -> physical pin 31)

# I2C
## No custom software depends on this, so double check in the current schematic when referencing
I2C_SDA = 2  # GPIO 2 (BCM mode -> physical pin 3)
I2C_SCL = 3  # GPIO 3 (BCM mode -> physical pin 5)

# MCU Reset Pins
## Mouth
MOUTH_RESET_PIN = 27  # GPIO 27 (BCM mode -> physical pin 13)
## Eyebrows (eyebrows share a single reset line)
EYEBROWS_RESET_PIN = 26  # GPIO 26 (BCM mode -> physical pin 37 on RPi 4B)
