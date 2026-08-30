cmake_minimum_required(VERSION 3.13)

include(pico_sdk_import.cmake)

project(i2c_test C CXX ASM)

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

pico_sdk_init()

# Add all the source files
file(GLOB SOURCES "*.c")

# Add i2c slave library
add_subdirectory(i2c_slave)

add_executable(i2c_test ${SOURCES})
target_link_libraries(i2c_test pico_stdlib i2c_slave)

pico_add_extra_outputs(i2c_test)
pico_enable_stdio_usb(i2c_test 1)
