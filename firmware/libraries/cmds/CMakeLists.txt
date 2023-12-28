add_library(artie_cmds INTERFACE)

target_include_directories(artie_cmds
    INTERFACE
    "."
)

target_sources(artie_cmds
    INTERFACE
    cmds.c
)

target_link_libraries(artie_cmds
    INTERFACE
    hardware_i2c
    i2c_slave
)
