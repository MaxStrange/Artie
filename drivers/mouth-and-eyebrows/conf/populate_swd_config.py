from artie_util import boardconfig_controller as board

right_contents = \
f"""# Use RPI GPIO pins
adapter driver bcm2835gpio

bcm2835gpio_speed_coeffs 146203 36

# SWD                swclk swdio
# Header pin numbers
bcm2835gpio_swd_nums {board.SWCLK_EYEBROW_RIGHT}    {board.SWDIO_EYEBROW_RIGHT}

transport select swd

adapter speed 1000

"""

left_contents = \
f"""# Use RPI GPIO pins
adapter driver bcm2835gpio

bcm2835gpio_speed_coeffs 146203 36

# SWD                swclk swdio
# Header pin numbers
bcm2835gpio_swd_nums {board.SWCLK_EYEBROW_LEFT}    {board.SWDIO_EYEBROW_LEFT}

transport select swd

adapter speed 1000

"""

mouth_contents = \
f"""
adapter driver bcm2835gpio

bcm2835gpio_speed_coeffs 146203 36

# SWD                swclk swdio
# Header pin numbers
bcm2835gpio_swd_nums {board.SWCLK_MOUTH}    {board.SWDIO_MOUTH}

transport select swd

adapter speed 1000

"""

with open("./raspberrypi-right-swd.cfg", 'w') as f:
    f.write(right_contents)

with open("./raspberrypi-swd.cfg", 'w') as f:
    f.write(left_contents)

with open("./raspberrypi-mouth-swd.cfg", 'w') as f:
    f.write(mouth_contents)
