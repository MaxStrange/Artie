"""
Metrics-related code for the eyebrows driver.
"""
from artie_util import artie_logging as alog
import enum

class SubmoduleNames(enum.StrEnum):
    """Names of the submodules in the eyebrows driver."""
    SERVO = "servo"
    LED = "led"
    LCD = "lcd"
    FIRMWARE = "fw"
