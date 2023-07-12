from artie_service_client import client as asc
from artie_util import boardconfig_controller as board
from artie_util import artie_logging as alog
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

def reset_mcu(mcu: MCU_IDS, artie_id: str):
    match mcu:
        case MCU_IDS.ALL:
            asc.reset(board.MCU_RESET_BROADCAST, artie_id=artie_id)
        case MCU_IDS.ALL_HEAD:
            asc.reset(board.MCU_RESET_ADDR_RL_EYEBROWS, artie_id=artie_id)
            asc.reset(board.MCU_RESET_ADDR_MOUTH, artie_id=artie_id)
            asc.reset(board.MCU_RESET_ADDR_HEAD_SENSORS, artie_id=artie_id)
            asc.reset(board.MCU_RESET_ADDR_PUMP_CTL, artie_id=artie_id)
        case MCU_IDS.EYEBROWS:
            asc.reset(board.MCU_RESET_ADDR_RL_EYEBROWS, artie_id=artie_id)
        case MCU_IDS.MOUTH:
            asc.reset(board.MCU_RESET_ADDR_MOUTH, artie_id=artie_id)
        case MCU_IDS.SENSORS_HEAD:
            asc.reset(board.MCU_RESET_ADDR_HEAD_SENSORS, artie_id=artie_id)
        case MCU_IDS.PUMP_CONTROL:
            asc.reset(board.MCU_RESET_ADDR_PUMP_CTL, artie_id=artie_id)
        case _:
            alog.error(f"Given an MCU ID we don't support: {mcu}. Ignoring.")
