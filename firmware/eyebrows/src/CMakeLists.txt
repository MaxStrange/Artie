cmake_minimum_required(VERSION 3.13)
include(pico_sdk_import.cmake)
project(eyebrows C CXX ASM)
set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

pico_sdk_init()

# Add top-level source and header files
file(GLOB SOURCES
  "*.c"
  "board/*.c"
  "cmds/*.c"
  "graphics/*.c"
  "graphics/lcd/*/*.c"
  "leds/*.c"
  "servo/*.c"
)
include_directories(
  "."
  "board"
  "cmds"
  "graphics"
  "graphics/lcd/*"
  "leds"
  "servo"
)

add_subdirectory(i2c_slave)

add_executable(eyebrows ${SOURCES})
target_link_libraries(eyebrows
  pico_stdlib
  pico_multicore
  hardware_spi
  hardware_i2c
  hardware_pwm
  i2c_slave
  hardware_gpio
  hardware_clocks
)

pico_add_extra_outputs(eyebrows)
pico_enable_stdio_usb(eyebrows 1)
