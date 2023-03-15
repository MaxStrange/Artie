#! /usr/bin/python3
"""
A simple user-space driver for the on-board LED.
Communicates over dbus.
"""
from gi.repository import GLib
import argparse
import dbus
import dbus.service
import dbus.mainloop.glib
import queue
import RPi.GPIO as GPIO
import threading
import time

LED_PIN = 18  # GPIO 18 (BCM mode -> physical pin 12, at least on RPi 4B)
LED_ACTIVE_MODE = GPIO.HIGH  # LED PIN is active high
LED_INACTIVE_MODE = GPIO.LOW
BUS_NAME = "com.artie.LedInterface"


class Led(dbus.service.Object):
    def __init__(self, bus, objpath, state='heartbeat'):
        super().__init__(bus, objpath)
        self._led_pin = LED_PIN
        self._active_mode = LED_ACTIVE_MODE
        self._inactive_mode = LED_INACTIVE_MODE
        self._pwm_pattern_thread = None
        self._pwm_pattern_queue = queue.Queue()
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self._led_pin, GPIO.OUT)
        GPIO.output(self._led_pin, self._inactive_mode)
        match state:
            case 'on':
                self.on()
            case 'off':
                self.off()
            case 'heartbeat':
                self.heartbeat()
            case _:
                raise ValueError(f"Invalid state for Led requested: {state}")

    @dbus.service.method(BUS_NAME, in_signature="", out_signature="")
    def on(self):
        """
        Turn the LED on.
        """
        self._clean_up_pwm_pattern_thread()
        GPIO.output(self._led_pin, self._active_mode)

    @dbus.service.method(BUS_NAME, in_signature="", out_signature="")
    def off(self):
        """
        Turn the LED off.
        """
        self._clean_up_pwm_pattern_thread()
        GPIO.output(self._led_pin, self._inactive_mode)

    @dbus.service.method(BUS_NAME, in_signature="", out_signature="")
    def heartbeat(self):
        """
        Set the LED to heartbeat mode.
        """
        if self._pwm_pattern_thread is None:
            self._spawn_pwm_pattern_thread()

    def _spawn_pwm_pattern_thread(self):
        def heartbeat(led_pin, period_seconds, q: queue.Queue):
            hz = 100
            pwm = GPIO.PWM(led_pin, hz)
            pwm.start(0)
            nsteps = 100
            timeout = (0.5 * period_seconds) / nsteps
            while True:
                for duty_cycle in range(0, nsteps):
                    try:
                        q.get(block=True, timeout=timeout)
                        return
                    except queue.Empty:
                        pwm.ChangeDutyCycle(duty_cycle)
                for duty_cycle in reversed([i for i in range(0, nsteps)]):
                    try:
                        q.get(block=True, timeout=timeout)
                        return
                    except queue.Empty:
                        pwm.ChangeDutyCycle(duty_cycle)

        period_seconds = 2.0
        self._pwm_pattern_thread = threading.Thread(target=heartbeat, args=(self._led_pin, period_seconds, self._pwm_pattern_queue), daemon=True)
        self._pwm_pattern_thread.start()

    def _clean_up_pwm_pattern_thread(self):
        if self._pwm_pattern_thread is not None:
            self._pwm_pattern_queue.put("END")
            self._pwm_pattern_thread.join()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=('on', 'off', 'heartbeat'), type=str, help="The particular mode of LED operation.")
    args = parser.parse_args()

    session_bus = dbus.SessionBus()
    name = dbus.service.BusName(BUS_NAME)
    led = Led(session_bus, "/Led", state=args.mode)
    mainloop = GLib.MainLoop()
    mainloop.run()
