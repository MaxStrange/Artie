"""
Common code for the eyebrows.
"""
from artie_util import artie_logging as alog
from artie_util import boardconfig_controller as board

# I2C address for each eyebrow MCU
MCU_ADDRESS_MAP = {
    "left": board.I2C_ADDRESS_EYEBROWS_MCU_LEFT,
    "right": board.I2C_ADDRESS_EYEBROWS_MCU_RIGHT,
}

def get_address(side: str):
    """
    Return the address corresponding to the given `side`.
    Raise a ValueError if 'side' is not one of 'left' or 'right'.
    """
    address = MCU_ADDRESS_MAP.get(side, None)
    if address is None:
        errmsg = f"Given side: '{side}', but must be 'left' or 'right'."
        alog.error(errmsg)
        raise ValueError(errmsg)
    else:
        return address
