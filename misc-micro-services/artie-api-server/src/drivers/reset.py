from artie_service_client import client as asc
from artie_util import boardconfig_controller as board
from artie_util import artie_logging as alog
from typing import Dict, Tuple
import enum

class MCU_IDS(enum.StrEnum):
    ALL = "all"
    ALL_HEAD = "all-head"
    EYEBROWS = "eyebrows"
    MOUTH = "mouth"
    SENSORS_HEAD = "sensors-head"
    PUMP_CONTROL = "pump-control"

class SBC_IDS(enum.StrEnum):
    ALL = "all"
    ALL_HEAD = "all-head"
    CONTROLLER = "controller"

def reset_mcu(mcu: MCU_IDS, artie_id: str) -> bool:
    match mcu:
        case MCU_IDS.ALL:
            return asc.reset(board.MCU_RESET_BROADCAST, artie_id=artie_id)
        case MCU_IDS.ALL_HEAD:
            worked = True
            worked &= asc.reset(board.MCU_RESET_ADDR_RL_EYEBROWS, artie_id=artie_id)
            worked &= asc.reset(board.MCU_RESET_ADDR_MOUTH, artie_id=artie_id)
            worked &= asc.reset(board.MCU_RESET_ADDR_HEAD_SENSORS, artie_id=artie_id)
            worked &= asc.reset(board.MCU_RESET_ADDR_PUMP_CTL, artie_id=artie_id)
            return worked
        case MCU_IDS.EYEBROWS:
            return asc.reset(board.MCU_RESET_ADDR_RL_EYEBROWS, artie_id=artie_id)
        case MCU_IDS.MOUTH:
            return asc.reset(board.MCU_RESET_ADDR_MOUTH, artie_id=artie_id)
        case MCU_IDS.SENSORS_HEAD:
            return asc.reset(board.MCU_RESET_ADDR_HEAD_SENSORS, artie_id=artie_id)
        case MCU_IDS.PUMP_CONTROL:
            return asc.reset(board.MCU_RESET_ADDR_PUMP_CTL, artie_id=artie_id)
        case _:
            alog.error(f"Given an MCU ID we don't support: {mcu}. Ignoring.")

def get_status(artie_id: str) -> Tuple[None|int, str|Dict[str, str]]:
    """
    Gets the status (a Dict of the form {submodule: status}). Returns a tuple of the form
    (None|errorcode, status|errmsg)
    """
    try:
        connection = asc.ServiceConnection(asc.Service.RESET_SERVICE, artie_id=artie_id)
        status = connection.status()
        return None, status
    except TimeoutError as e:
        return 504, f"Timed out trying to get the reset status: {e}"
    except Exception as e:
        return 500, f"Error trying to get the reset status: {e}"

def self_test(artie_id: str) -> Tuple[None|int, None|str]:
    """
    Do the reset self test. Returns a tuple of the form
    (None|errorcode, None|errmsg)
    """
    try:
        connection = asc.ServiceConnection(asc.Service.RESET_SERVICE, artie_id=artie_id)
        connection.self_check()
    except TimeoutError as e:
        return 504, f"Timed out trying to do the reset self test: {e}"
    except Exception as e:
        return 500, f"Error trying to reload the reset self test: {e}"
    return None, None
