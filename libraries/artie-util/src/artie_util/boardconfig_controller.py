"""
This is the board config for the controller node.
"""
########################### CONFIGURATION v0.1 ###################################
## SWD
### Mouth
#SWDIO_MOUTH = 22  # GPIO 22 (BCM mode -> physical pin 15)
#SWCLK_MOUTH = 23  # GPIO 23 (BCM mode -> physical pin 16)
### Left Eyebrow
#SWDIO_EYEBROW_LEFT = 24  # GPIO 24 (BCM mode -> physical pin 18)
#SWCLK_EYEBROW_LEFT = 25  # GPIO 25 (BCM mode -> physical pin 22)
### Right Eyebrow
#SWDIO_EYEBROW_RIGHT = 5  # GPIO  5 (BCM mode -> physical pin 29)
#SWCLK_EYEBROW_RIGHT = 6  # GPIO  6 (BCM mode -> physical pin 31)
#
## MCU Reset Pins
### Mouth
#MOUTH_RESET_PIN = 27  # GPIO 27 (BCM mode -> physical pin 13)
### Eyebrows (eyebrows share a single reset line)
#EYEBROWS_RESET_PIN = 26  # GPIO 26 (BCM mode -> physical pin 37 on RPi 4B)


########################## CONFIGURATION v0.2 #####################################
# Reset addresses
MCU_RESET_ADDR_RL_EYEBROWS = 0x00
MCU_RESET_ADDR_MOUTH = 0x01
MCU_RESET_ADDR_HEAD_SENSORS = 0x02
MCU_RESET_ADDR_PUMP_CTL = 0x03
MCU_RESET_BROADCAST = 0xFF

# SWD - these MCUs are not on CAN bus. They update by means of SWD.
## Mouth
SWDIO_MOUTH = 22  # GPIO 22 (BCM mode -> physical pin 15)
SWCLK_MOUTH = 23  # GPIO 23 (BCM mode -> physical pin 16)
## Left Eyebrow
SWDIO_EYEBROW_LEFT = 24  # GPIO 24 (BCM mode -> physical pin 18)
SWCLK_EYEBROW_LEFT = 25  # GPIO 25 (BCM mode -> physical pin 22)
## Right Eyebrow
SWDIO_EYEBROW_RIGHT = 5  # GPIO  5 (BCM mode -> physical pin 29)
SWCLK_EYEBROW_RIGHT = 6  # GPIO  6 (BCM mode -> physical pin 31)
## Reset Addressing MCU
SWDIO_RESET = 4   # GPIO 4  (BCM mode -> physical pin 7)
SWCLK_RESET = 12  # GPIO 12 (BCM mode -> physical pin 32)
RESET_RESET = 13  # GPIO 13 (BCM mode -> physical pin 33)


########################## COMMON CONFIGURATION ####################################
# SPI for CAN Bus
SPI_CSCAN = 8   # GPIO  8 (BCM Mode -> physical pin 24)
SPI_MISO  = 9   # GPIO  9 (BCM Mode -> physical pin 21)
SPI_MOSI  = 10  # GPIO 10 (BCM Mode -> physical pin 19)
SPI_SCLK  = 11  # GPIO 11 (BCM Mode -> physical pin 23)
CAN_INT   = 27  # GPIO 27 (BCM Mode -> physical pin 13)

# UART
UART_TX = 14  # GPIO 14 (BCM mode -> physical pin 8)
UART_RX = 15  # GPIO 15 (BCM mode -> physical pin 10)
UART_CTS = 16 # GPIO 16 (BCM mode -> physical pin 36)
UART_RTS = 17 # GPIO 17 (BCM mode -> physical pin 11)

# LED Pin
LED_PIN = 18  # GPIO 18 (BCM mode -> physical pin 12, at least on RPi 4B)

# I2C
I2C_SDA = 2  # GPIO 2 (BCM mode -> physical pin 3)
I2C_SCL = 3  # GPIO 3 (BCM mode -> physical pin 5)
I2C_ADDRESS_EYEBROWS_MCU_LEFT = 0x17
I2C_ADDRESS_EYEBROWS_MCU_RIGHT = 0x18
I2C_ADDRESS_MOUTH_MCU = 0x19
I2C_ADDRESS_RESET_MCU = 0x20
