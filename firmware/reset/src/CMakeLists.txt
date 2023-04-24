cmake_minimum_required(VERSION 3.13)
include(pico_sdk_import.cmake)
project(reset-mcu C CXX ASM)
set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

pico_sdk_init()

# Add compiler definitions
add_compile_definitions(LOG_LEVEL=${LOG_LEVEL})

# Compiler warnings
add_compile_options(-Wall -Wextra -Werror -Wno-unused-function -Wno-unused-parameter)

# Add top-level source and header files
file(GLOB SOURCES
  "*.c"
)
include_directories(
  "."
)

add_subdirectory(i2c_slave)

add_executable(reset-mcu ${SOURCES})
target_link_libraries(reset-mcu
  pico_stdlib
  hardware_i2c
  i2c_slave
)

pico_add_extra_outputs(reset-mcu)
pico_enable_stdio_usb(reset-mcu 1)
