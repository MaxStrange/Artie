"""
All the stuff that depends on the PCB or Pi model.
"""
from artie_util import util
if util.on_linux():
    import RPi.GPIO as GPIO

LED_PIN = 18  # GPIO 18 (BCM mode -> physical pin 12, at least on RPi 4B)
LED_ACTIVE_MODE = GPIO.HIGH if util.on_linux() else None  # LED PIN is active high
LED_INACTIVE_MODE = GPIO.LOW if util.on_linux() else None
