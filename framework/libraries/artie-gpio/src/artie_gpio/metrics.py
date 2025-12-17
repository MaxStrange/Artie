"""
Metrics definitions for the Artie GPIO library.
"""
import enum

class Attributes:
    """
    Attributes for GPIO metrics.
    """
    PIN = "gpio.pin"
    """The GPIO pin number."""

    LEVEL = "gpio.level"
    """The GPIO level (HIGH or LOW)."""
