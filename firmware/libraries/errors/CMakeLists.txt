add_library(artie_err INTERFACE)

target_include_directories(artie_err
    INTERFACE
    "."
)

target_sources(artie_err
    INTERFACE
    errors.c
)
