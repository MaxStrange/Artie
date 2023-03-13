"""
Module for controlling GPIO on the controller board.
"""
from . import boardconfig
from artie_util import util
import queue
import threading
import time

if util.on_linux():
    import RPi.GPIO as GPIO

# The singleton Gpio class instance
gpio = None

# How long we wait before exiting after setting the LED on
LED_WAIT_SECONDS = 3

def public_gpio_function(func):
    """
    Initializes the GPIO object if not already initialized.
    """
    def modified_function(*args, **kwargs):
        global gpio
        if gpio is None:
            gpio = Gpio()

        return func(*args, **kwargs)
    return modified_function

class Gpio:
    def __init__(self) -> None:
        self._led_pin = boardconfig.LED_PIN
        self._active_mode = boardconfig.LED_ACTIVE_MODE
        self._inactive_mode = boardconfig.LED_INACTIVE_MODE
        self._pwm_pattern_thread = None
        self._pwm_pattern_queue = queue.Queue()
        if util.on_linux():
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self._led_pin, GPIO.OUT)
            GPIO.output(self._led_pin, self._inactive_mode)

    def led_on(self):
        self._clean_up_pwm_pattern_thread()

        if util.on_linux():
            GPIO.output(self._led_pin, self._active_mode)
            time.sleep(LED_WAIT_SECONDS)
        else:
            print("Simulating turning LED ON")

    def led_off(self):
        self._clean_up_pwm_pattern_thread()

        if util.on_linux():
            GPIO.output(self._led_pin, self._inactive_mode)
        else:
            print("Simulating turning LED OFF")

    def led_heartbeat(self):
        if self._pwm_pattern_thread is not None:
            return  # Nothing to do

        if util.on_linux():
            self._spawn_pwm_pattern_thread()
            time.sleep(LED_WAIT_SECONDS)
            self.led_off()
        else:
            print("Simulating setting LED to heartbeat mode")

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

@public_gpio_function
def led_on():
    """
    Turn the LED on.
    """
    gpio.led_on()

@public_gpio_function
def led_off():
    """
    Turn the LED off.
    """
    gpio.led_off()

@public_gpio_function
def led_heartbeat():
    """
    Set the LED mode to heartbeat.
    """
    gpio.led_heartbeat()
