"""
The main entry to the Artie GPIO library.
"""
from . import metrics
from artie_util import util
from artie_util import artie_logging as alog
import os

# At the end of this gnarly initialization bit,
# we should have a MODE which, if it isn't 'testing',
# means we also have a GPIO library imported.
# In the case of 'testing', we don't have a GPIO
# imported into the system
if not util.on_linux():
    # Definitely an unsupported environment. Assume we want test mode.
    alog.info("Detected we are not running on Linux. Assuming test environment.")
    MODE = 'testing'
elif "arm" not in os.uname().machine:
    # Probably x86/amd64
    alog.info("Detected Linux, but not an ARM device. Assuming test environment.")
    MODE = 'testing'
else:
    # Try to use RPi.GPIO
    try:
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)
        MODE = 'rpi'
    except (ModuleNotFoundError, RuntimeError):
        # Can't run GPIO on this system, must not be RPi
        try:
            import Jetson.GPIO as GPIO
            MODE = 'jetson'
        except ModuleNotFoundError:
            raise OSError("Can't figure out what type of OS or platform we are running on.")

# High GPIO value
HIGH = 'HIGH' if MODE == 'testing' else GPIO.HIGH

# Low GPIO value
LOW = 'LOW' if MODE == 'testing' else GPIO.LOW

# GPIO input mode
IN = 'IN' if MODE == 'testing' else GPIO.IN

# GPIO output mode
OUT = 'OUT' if MODE == 'testing' else GPIO.OUT

def setup(pin, mode):
    """
    Set up the given pin in the given mode.
    """
    if MODE == 'testing':
        alog.info(f"Setting up pin {pin} with mode {mode}")
    else:
        GPIO.setup(pin, mode)

def output(pin, level):
    """
    Set the given pin to the given level.
    """
    alog.update_counter(1, "count", alog.MetricHWBusGPIOOrder.PIN_OUTPUT, unit=alog.MetricUnits.CALLS, description="Number of times voltage has been output on pins", attributes={metrics.Attributes.PIN: pin, metrics.Attributes.LEVEL: level})
    if MODE == 'testing':
        alog.info(f"Setting pin {pin} to level {level}")
    else:
        GPIO.output(pin, level)
