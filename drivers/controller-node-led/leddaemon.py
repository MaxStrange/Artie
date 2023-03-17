#! /usr/bin/python3
"""
A simple user-space driver for the on-board LED.
Communicates over dbus.
"""
from artie_util import boardconfig_controller as board
import argparse
import logging
import os
import queue
import socket
import RPi.GPIO as GPIO
import threading

class Led:
    def __init__(self, state='heartbeat'):
        self._led_pin = board.LED_PIN
        self._active_mode = GPIO.HIGH
        self._inactive_mode = GPIO.LOW
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

    def on(self):
        """
        Turn the LED on.
        """
        logging.info("Setting LED to ON")
        self._clean_up_pwm_pattern_thread()
        GPIO.output(self._led_pin, self._active_mode)

    def off(self):
        """
        Turn the LED off.
        """
        logging.info("Setting LED to OFF")
        self._clean_up_pwm_pattern_thread()
        GPIO.output(self._led_pin, self._inactive_mode)

    def heartbeat(self):
        """
        Set the LED to heartbeat mode.
        """
        logging.info("Setting LED to HEARTBEAT")
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
            self._pwm_pattern_thread = None

def _serve(address, led):
    s = socket.socket(family=socket.AF_UNIX)
    s.bind(address)
    s.listen()

    while True:
        c, addr = s.accept()
        logging.info("Connected to a client.")
        match val := c.recv(1024).decode().lower():
            case "on":
                led.on()
            case "off":
                led.off()
            case "heartbeat":
                led.heartbeat()
            case _:
                logging.error(f"Ignoring an unexpected value from client connection: {val}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=('on', 'off', 'heartbeat'), type=str, help="The particular mode of LED operation.")
    parser.add_argument("-l", "--loglevel", type=str, default="info", choices=["debug", "info", "warning", "error"], help="The log level.")
    args = parser.parse_args()

    # Set up logging
    format = "%(asctime)s %(threadName)s %(levelname)s: %(message)s"
    logging.basicConfig(format=format, level=getattr(logging, args.loglevel.upper()))

    led = Led(state=args.mode)
    address = "/tmp/leddaemonconnection"
    try:
        # In case previous instance did not shut down cleanly
        if os.path.exists(address):
            os.remove(address)
        _serve(address, led)
    finally:
        # Cleanup the tmp file
        if os.path.exists(address):
            os.remove(address)
