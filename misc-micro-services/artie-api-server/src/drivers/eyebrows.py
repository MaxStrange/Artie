from artie_service_client import client as asc
from artie_util import artie_logging as alog
from typing import List
from typing import Tuple
import enum

class LEDStates(enum.StrEnum):
    ON = "on"
    OFF = "off"
    HEARTBEAT = "heartbeat"

def display(display_value: List[str], which: str, artie_id: str) -> Tuple[int|None, str|None]:
    """
    Returns a tuple of the form (error code|None, errmsg|None).
    """
    try:
        connection = asc.ServiceConnection(asc.Service.EYEBROWS_SERVICE, artie_id=artie_id)
        connection.lcd_draw(which, display_value)
    except TimeoutError as e:
        return 504, f"Timed out trying to draw on {which} eyebrow LCD: {e}"
    except Exception as e:
        return 500, f"Error trying to display something on {which} eyebrows LCD: {e}"
    return None, None

def get_display(which: str, artie_id: str) -> Tuple[None|int, List[str]|str]:
    """
    Returns a tuple of the form (None, LCD value) or (err code, errmsg).
    """
    try:
        connection = asc.ServiceConnection(asc.Service.EYEBROWS_SERVICE, artie_id=artie_id)
        val = connection.lcd_get(which)
        val = [v for v in val]
        return None, val
    except TimeoutError as e:
        return 504, f"Timed out trying to get the {which} eyebrow LCD display: {e}"
    except Exception as e:
        return 500, f"Error trying to get the {which} eyebrow LCD display: {e}"

def test(which: str, artie_id: str) -> Tuple[int|None, str|None]:
    """
    Returns a tuple of the form (error code|None, errmsg|None).
    """
    try:
        connection = asc.ServiceConnection(asc.Service.EYEBROWS_SERVICE, artie_id=artie_id)
        connection.lcd_test(which)
    except TimeoutError as e:
        return 504, f"Timed out trying to test the {which} eyebrow LCD display: {e}"
    except Exception as e:
        return 500, f"Error trying to test the {which} eyebrow LCD display: {e}"
    return None, None

def clear(which: str, artie_id: str) -> Tuple[int|None, str|None]:
    """
    Returns a tuple of the form (error code|None, errmsg|None).
    """
    try:
        connection = asc.ServiceConnection(asc.Service.EYEBROWS_SERVICE, artie_id=artie_id)
        connection.lcd_off(which)
    except TimeoutError as e:
        return 504, f"Timed out trying to clear the {which} eyebrow LCD display: {e}"
    except Exception as e:
        return 500, f"Error trying to clear the {which} eyebrow LCD display: {e}"
    return None, None

def led(which: str, state: LEDStates, artie_id: str) -> Tuple[int|None, str|None]:
    """
    Sets the mouth LED to the given state and returns a tuple of the form
    (errorcode|None, errmsg|None)
    """
    try:
        connection = asc.ServiceConnection(asc.Service.EYEBROWS_SERVICE, artie_id=artie_id)
        match state:
            case LEDStates.ON:
                connection.led_on(which)
            case LEDStates.OFF:
                connection.led_off(which)
            case LEDStates.HEARTBEAT:
                connection.led_heartbeat(which)
            case _:
                return 400, f"Invalid led state: {state}"
    except TimeoutError as e:
        return 504, f"Timed out trying to set the {which} eyebrow LED: {e}"
    except Exception as e:
        return 500, f"Error trying to set the {which} eyebrow LED: {e}"
    return None, None

def get_led(which: str, artie_id: str) -> Tuple[None|int, LEDStates|str]:
    """
    Returns a tuple of the form (None, LED value) or (err code, errmsg).
    """
    try:
        connection = asc.ServiceConnection(asc.Service.EYEBROWS_SERVICE, artie_id=artie_id)
        val = LEDStates(connection.led_get(which))
        return None, val
    except TimeoutError as e:
        return 504, f"Timed out trying to get the {which} eyebrow LED state: {e}"
    except Exception as e:
        return 500, f"Error trying to get the {which} eyebrow LED state: {e}"

def reload_firmware(artie_id: str) -> Tuple[int|None, str|None]:
    """
    Reloads the eyebrow MCU firmware (for both MCUs) and returns a tuple of the form
    (errorcode|None, errmsg|None)
    """
    try:
        connection = asc.ServiceConnection(asc.Service.EYEBROWS_SERVICE, artie_id=artie_id)
        connection.firmware_load()
    except TimeoutError as e:
        return 504, f"Timed out trying to reload the eyebrow FW: {e}"
    except Exception as e:
        return 500, f"Error trying to reload the eyebrow FW: {e}"
    return None, None

def set_servo(which: str, degrees: float, artie_id: str) -> Tuple[int|None, str|None]:
    """
    Sets the given servo to the given position. Returns a tuple of the form
    (errorcode|None, errmsg|degrees)
    """
    try:
        connection = asc.ServiceConnection(asc.Service.EYEBROWS_SERVICE, artie_id=artie_id)
        connection.servo_go(which, degrees)
    except TimeoutError as e:
        return 504, f"Timed out trying to set the {which} eyebrow servo to {degrees} degrees: {e}"
    except Exception as e:
        return 500, f"Error trying to set the {which} eyebrow servo to {degrees} degrees: {e}"
    return None, None

def get_servo(which: str, artie_id: str) -> Tuple[int|None, str|float]:
    """
    Gets the servo position for `which` side. Returns a tuple of the form
    (errcode|None, errmsg|degrees)
    """
    try:
        connection = asc.ServiceConnection(asc.Service.EYEBROWS_SERVICE, artie_id=artie_id)
        val = float(connection.servo_get(which))
        return None, val
    except TimeoutError as e:
        return 504, f"Timed out trying to get the {which} eyebrow servo position: {e}"
    except Exception as e:
        return 500, f"Error trying to get the {which} eyebrow servo position: {e}"
