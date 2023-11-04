from artie_service_client import client as asc
from artie_util import artie_logging as alog
from typing import Tuple
import enum

class MouthValues(enum.StrEnum):
    SMILE = "smile"
    FROWN = "frown"
    LINE = "line"
    SMIRK = "smirk"
    OPEN = "open"
    OPEN_SMILE = "open-smile"
    ZIG_ZAG = "zig-zag"
    TALKING = "talking"

class LEDStates(enum.StrEnum):
    ON = "on"
    OFF = "off"
    HEARTBEAT = "heartbeat"

def display(display_value: MouthValues, artie_id: str) -> Tuple[int|None, str|None]:
    """
    Returns a tuple of the form (error code|None, errmsg|None).
    """
    try:
        connection = asc.ServiceConnection(asc.Service.MOUTH_SERVICE, artie_id=artie_id)
        if display_value == MouthValues.TALKING:
            worked = connection.lcd_talk()
        else:
            worked = connection.lcd_draw(display_value)
        if not worked:
            return 500, f"Error trying to display something on the LCD. The LCD is not working."
    except TimeoutError as e:
        return 504, f"Timed out trying to draw on mouth LCD: {e}"
    except Exception as e:
        return 500, f"Error trying to display something on the LCD: {e}"
    return None, None

def get_display(artie_id: str) -> Tuple[None|int, MouthValues|str]:
    """
    Returns a tuple of the form (None, LCD value) or (err code, errmsg).
    """
    try:
        connection = asc.ServiceConnection(asc.Service.MOUTH_SERVICE, artie_id=artie_id)
        val = str(connection.lcd_get())
        return None, val
    except TimeoutError as e:
        return 504, f"Timed out trying to get the mouth LCD display: {e}"
    except Exception as e:
        return 500, f"Error trying to get the mouth LCD display: {e}"

def test(artie_id: str) -> Tuple[int|None, str|None]:
    """
    Returns a tuple of the form (error code|None, errmsg|None).
    """
    try:
        connection = asc.ServiceConnection(asc.Service.MOUTH_SERVICE, artie_id=artie_id)
        worked = connection.lcd_test()
        if not worked:
            return 500, f"Error trying to test the mouth LCD display. The display is not working."
    except TimeoutError as e:
        return 504, f"Timed out trying to test the mouth LCD display: {e}"
    except Exception as e:
        return 500, f"Error trying to test the mouth LCD display: {e}"
    return None, None

def clear(artie_id: str) -> Tuple[int|None, str|None]:
    """
    Returns a tuple of the form (error code|None, errmsg|None).
    """
    try:
        connection = asc.ServiceConnection(asc.Service.MOUTH_SERVICE, artie_id=artie_id)
        worked = connection.lcd_off()
        if not worked:
            return 500, f"Error trying to clear the mouth LCD display. The display is not working."
    except TimeoutError as e:
        return 504, f"Timed out trying to clear the mouth LCD display: {e}"
    except Exception as e:
        return 500, f"Error trying to clear the mouth LCD display: {e}"
    return None, None

def led(state: LEDStates, artie_id: str) -> Tuple[int|None, str|None]:
    """
    Sets the mouth LED to the given state and returns a tuple of the form
    (errorcode|None, errmsg|None)
    """
    try:
        worked = True
        connection = asc.ServiceConnection(asc.Service.MOUTH_SERVICE, artie_id=artie_id)
        match state:
            case LEDStates.ON:
                worked = connection.led_on()
            case LEDStates.OFF:
                worked = connection.led_off()
            case LEDStates.HEARTBEAT:
                worked = connection.led_heartbeat()
            case _:
                return 400, f"Invalid led state: {state}"
        if not worked:
            return 500, f"Error trying to set the mouth LED. The LED is not working."
    except TimeoutError as e:
        return 504, f"Timed out trying to set the mouth LED: {e}"
    except Exception as e:
        return 500, f"Error trying to set the mouth LED: {e}"
    return None, None

def get_led(artie_id: str) -> Tuple[None|int, LEDStates|str]:
    """
    Returns a tuple of the form (None, LED value) or (err code, errmsg).
    """
    try:
        connection = asc.ServiceConnection(asc.Service.MOUTH_SERVICE, artie_id=artie_id)
        val = LEDStates(connection.led_get())
        return None, val
    except TimeoutError as e:
        return 504, f"Timed out trying to get the mouth LED state: {e}"
    except Exception as e:
        return 500, f"Error trying to get the mouth LED state: {e}"

def reload_firmware(artie_id: str) -> Tuple[int|None, str|None]:
    """
    Reloads the mouth MCU's firmware and returns a tuple of the form
    (errorcode|None, errmsg|None)
    """
    try:
        connection = asc.ServiceConnection(asc.Service.MOUTH_SERVICE, artie_id=artie_id)
        worked = connection.firmware_load()
        if not worked:
            return 500, f"Error trying to reload the mouth FW. The FW subsystem is not working."
    except TimeoutError as e:
        return 504, f"Timed out trying to reload the mouth FW: {e}"
    except Exception as e:
        return 500, f"Error trying to reload the mouth FW: {e}"
    return None, None
