cmake_minimum_required(VERSION 3.10)

# Unity testing framework
add_library(unity STATIC
    unity/unity.c
    unity/unity.h
    unity/unity_internals.h
)

target_include_directories(unity PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/unity
)

# Test utilities library
add_library(test_utils STATIC
    util.c
    util.h
)

target_include_directories(test_utils PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CMAKE_SOURCE_DIR}/include
)

# Link against Unity so test utilities can use Unity assertions
target_link_libraries(test_utils PUBLIC unity)

# Helper function to create test executables
function(add_artie_can_test test_name)
    add_executable(${test_name} ${test_name}.c)

    # Link against Unity, test utilities, and artie-can
    target_link_libraries(${test_name} PRIVATE unity test_utils)

    # Link against the static library if it exists, otherwise shared
    if(TARGET artie_can_static)
        target_link_libraries(${test_name} PRIVATE artie_can_static)
    elseif(TARGET artie_can)
        target_link_libraries(${test_name} PRIVATE artie_can)
    else()
        message(FATAL_ERROR "No artie_can library target found")
    endif()

    # Include directories
    target_include_directories(${test_name} PRIVATE
        ${CMAKE_SOURCE_DIR}/include
    )

    # Platform-specific settings
    if(WIN32)
        # Windows-specific: link against ws2_32 for socket functions
        target_link_libraries(${test_name} PRIVATE ws2_32)
        target_compile_definitions(${test_name} PRIVATE _CRT_SECURE_NO_WARNINGS)
    else()
        # Unix-specific: link against pthread and m (math)
        target_link_libraries(${test_name} PRIVATE pthread m)
    endif()

    # Add test to CTest
    add_test(NAME ${test_name} COMMAND ${test_name})

    # Set working directory for the test
    set_tests_properties(${test_name} PROPERTIES
        WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
    )
endfunction()

# Add individual test files here (no *.c suffix)
add_artie_can_test(test_rtacp)
add_artie_can_test(test_bwacp)
add_artie_can_test(test_bwacp_frame_loss)
add_artie_can_test(test_psacp)
add_artie_can_test(test_psacp_frame_loss)
add_artie_can_test(test_rpcacp)

# Print test information
message(STATUS "Unity test framework configured")
message(STATUS "Tests will be built in: ${CMAKE_CURRENT_BINARY_DIR}")
