add_library(artie_led INTERFACE)

target_include_directories(artie_led
    INTERFACE
    "."
)

target_sources(artie_led
    INTERFACE
    leds.c
)

target_link_libraries(artie_led
    INTERFACE
    hardware_gpio
    hardware_pwm
)
