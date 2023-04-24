from artie_util import boardconfig_controller as board

contents = \
f"""
adapter driver bcm2835gpio

bcm2835gpio_speed_coeffs 146203 36

# SWD                swclk swdio
# Header pin numbers
bcm2835gpio_swd_nums {board.SWCLK_RESET}    {board.SWDIO_RESET}

transport select swd

adapter speed 1000

"""

with open("./raspberrypi-reset-swd.cfg", 'w') as f:
    f.write(contents)
