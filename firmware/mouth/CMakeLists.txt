cmake_minimum_required(VERSION 3.13)
include(pico_sdk_import.cmake)
project(mouth C CXX ASM)
set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

pico_sdk_init()

# Add compiler definitions
add_compile_definitions(MOUTH=1)
add_compile_definitions(LOG_LEVEL=${LOG_LEVEL})

# Set compiler warnings
add_compile_options(-Wall -Wextra -Werror -Wno-unused-function -Wno-unused-parameter)

# Add top-level source and header files
file(GLOB SOURCES
  "*.c"
  "board/*.c"
  "graphics/*.c"
  "graphics/lcd/*/*.c"
)
include_directories(
  "."
  "board"
  "cmds"
  "graphics"
  "graphics/lcd/*"
  "leds"
)

add_subdirectory(i2c_slave)
add_subdirectory(leds)
add_subdirectory(errors)
add_subdirectory(cmds)

add_executable(mouth ${SOURCES})
target_link_libraries(mouth
  pico_stdlib
  pico_multicore
  hardware_spi
  hardware_i2c
  hardware_pwm
  i2c_slave
  artie_led
  artie_err
  artie_cmds
  hardware_gpio
  hardware_clocks
  pico_time
)

pico_add_extra_outputs(mouth)
pico_enable_stdio_usb(mouth 1)
