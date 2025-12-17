"""
Metrics-related code for the mouth driver.
"""
from artie_util import artie_logging as alog
import enum

class SubmoduleNames(enum.StrEnum):
    """Names of the submodules in the mouth driver."""
    LED = "led"
    LCD = "lcd"
    FIRMWARE = "fw"
