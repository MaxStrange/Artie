"""
CFFI build script for the Artie CAN Python bindings.

This runs in CFFI's *API mode*: the declarations in CDEF below are compiled against the real
headers, so the C compiler is what decides struct sizes, field offsets and enum values. Structs
that Python only ever needs to own and hand back to the library (contexts, backend handles) are
declared partially - a bare `...;` member tells CFFI "there are more fields here, go read the
header". That is the whole reason for preferring CFFI over a hand-written ctypes mirror of, say,
`rpcacp_context_t`: a mirror that drifts from the header corrupts memory silently, whereas this
either compiles correctly or fails the build.

The library's C sources are compiled directly into the extension module, so an installed
`artie_can` is self-contained - there is no separate shared library to locate at import time, and
CMake is not needed to `pip install .`.
"""
import os
import pathlib
import sys

from cffi import FFI

HERE = pathlib.Path(__file__).parent.resolve()

# setuptools rejects absolute paths in `sources`, so every path handed to set_source() below stays
# relative to this directory. That means the build has to run from here, which is where setuptools
# invokes it from and where __main__ chdirs to.

# Kept in step with ARTIE_CAN_SOURCES in CMakeLists.txt.
SOURCES = [
    "src/backend/backend_mcp2515.c",
    "src/backend/driver_mcp2515.c",
    "src/backend/backend_udp_mcast.c",
    "src/protocol/rtacp.c",
    "src/protocol/bwacp.c",
    "src/protocol/rpcacp.c",
    "src/protocol/psacp.c",
    "src/util/circular_buffer.c",
    "src/util/log.c",
    "src/util/translationlayer.c",
    "src/util/util.c",
    "src/artie_can_core.c",
]

INCLUDE_DIRS = [
    "include",
    "include/backend",
    "include/protocol",
    "include/util",
]

# Everything the Python bindings need to see. Anything not listed here is invisible to Python,
# which is deliberate: the ISR-facing and protocol-internal entry points (`*_receive_in_isr`,
# `*_tick`) are driven by the library itself and have no business being called from Python.
CDEF = r"""
/* ---------------------------------------------------------------- err.h */

typedef enum {
    ARTIE_CAN_ERR_NONE,
    ARTIE_CAN_ERR_INVALID_ARG,
    ARTIE_CAN_ERR_TIMEOUT,
    ARTIE_CAN_ERR_NO_DATA,
    ARTIE_CAN_ERR_SEND_FAIL,
    ARTIE_CAN_ERR_RECEIVE_FAIL,
    ARTIE_CAN_ERR_INIT_FAIL,
    ARTIE_CAN_ERR_CLOSE_FAIL,
    ARTIE_CAN_ERR_CLOSED,
    ARTIE_CAN_ERR_SEND_BUSY,
    ARTIE_CAN_ERR_NO_SPACE,
    ARTIE_CAN_ERR_INTERNAL,
    ARTIE_CAN_ERR_DRIVER,
    ARTIE_CAN_ERR_NO_RESPONSE,
    ...
} artie_can_error_t;

/* -------------------------------------------------------------- frame.h */

#define ARTIE_CAN_FRAME_MAX_DATA_LENGTH ...
#define ARTIE_CAN_FRAME_ID_PROTOCOL_LOCATION ...
#define ARTIE_CAN_FRAME_ID_PROTOCOL_MASK ...
#define ARTIE_CAN_FRAME_ID_SENDER_ADDRESS_LOCATION ...
#define ARTIE_CAN_FRAME_ID_SENDER_ADDRESS_MASK ...
#define ARTIE_CAN_FRAME_ID_TARGET_ADDRESS_LOCATION ...
#define ARTIE_CAN_FRAME_ID_TARGET_ADDRESS_MASK ...
#define ARTIE_CAN_MAX_NODES ...

typedef struct {
    uint32_t id;
    uint8_t dlc;
    uint8_t data[...];
    ...;
} artie_can_frame_t;

/* ------------------------------------------------------------ context.h */

typedef void (*artie_can_rx_callback_t)(const artie_can_frame_t *frame);
typedef uint64_t artie_can_get_ms_t(void);

typedef enum {
    ARTIE_CAN_PROTOCOL_FLAG_RTACP,
    ARTIE_CAN_PROTOCOL_FLAG_RPCACP,
    ARTIE_CAN_PROTOCOL_FLAG_PSACP,
    ARTIE_CAN_PROTOCOL_FLAG_BWACP,
    ...
} artie_can_protocol_t;

/* Partially declared: only the fields Python reads back out are named. */
typedef struct {
    uint32_t receive_bytes_written;
    uint32_t receive_address;
    uint32_t receive_buffer_size;
    ...;
} bwacp_context_t;

typedef struct {
    bwacp_context_t bwacp_context;
    uint16_t protocol_flags;
    uint8_t node_address;
    ...;
} artie_can_context_t;

typedef struct { ...; } artie_can_backend_t;

typedef enum {
    ARTIE_CAN_BACKEND_MCP2515,
    ARTIE_CAN_BACKEND_UDP_MCAST,
    ...
} artie_can_backend_type_t;

/* ---------------------------------------------------------- artie_can.h */

artie_can_error_t artie_can_init(artie_can_context_t *context, artie_can_backend_t *handle,
                                 artie_can_backend_type_t backend_type,
                                 artie_can_rx_callback_t rx_callback,
                                 artie_can_get_ms_t *get_ms_fn);
artie_can_error_t artie_can_close(artie_can_backend_t *handle);
artie_can_error_t artie_can_tick(artie_can_backend_t *handle);
artie_can_error_t artie_can_tick_isr(artie_can_backend_t *handle);

/* -------------------------------------------------- backend_udp_mcast.h */

#define ARTIE_CAN_UDP_MCAST_ADDR_MAX_LENGTH ...

typedef struct { ...; } artie_can_udp_mcast_context_t;

artie_can_error_t artie_can_init_context_udp_mcast(artie_can_context_t *context,
                                                   artie_can_udp_mcast_context_t *udp_mcast_context,
                                                   const char *multicast_group, uint16_t port);

/* ------------------------------------ backend_mcp2515.h (+ its context) */

typedef enum {
    MCP2515_MODE_NORMAL,
    MCP2515_MODE_SLEEP,
    MCP2515_MODE_LOOPBACK,
    MCP2515_MODE_LISTEN_ONLY,
    MCP2515_MODE_CONFIGURATION,
    ...
} mcp2515_mode_t;

typedef struct {
    bool bfp0_int_enabled;
    bool bfp1_int_enabled;
    mcp2515_mode_t mode;
    uint32_t oscillator_freq_hz;
    ...;
} driver_mcp2515_config_t;

typedef artie_can_error_t (*artie_can_write_byte_t)(artie_can_context_t *context, uint8_t byte);
typedef artie_can_error_t (*artie_can_write_cs_pin_t)(artie_can_context_t *context, bool cs_low);

typedef struct {
    uint8_t read_byte;
    ...;
} artie_can_mcp2515_context_t;

artie_can_error_t artie_can_init_context_mcp2515(artie_can_context_t *context,
                                                 artie_can_mcp2515_context_t *mcp2515_ctx,
                                                 driver_mcp2515_config_t *driver_config,
                                                 artie_can_write_byte_t write_byte_fn,
                                                 artie_can_write_cs_pin_t write_cs_pin_fn);

/* -------------------------------------------------------------- rtacp.h */

#define ARTIE_CAN_RTACP_TARGET_ADDRESS_BROADCAST ...
#define ARTIE_CAN_RTACP_MAX_DATA_BYTES ...
#define ARTIE_CAN_RTACP_PROTOCOL_ID ...
#define ARTIE_CAN_RTACP_ACK_TIMEOUT_MS ...

typedef enum {
    ARTIE_CAN_FRAME_PRIORITY_RTACP_LOW,
    ARTIE_CAN_FRAME_PRIORITY_RTACP_MEDIUM,
    ARTIE_CAN_FRAME_PRIORITY_RTACP_HIGH,
    ARTIE_CAN_FRAME_PRIORITY_RTACP_HIGHEST,
    ...
} artie_can_frame_priority_rtacp_t;

typedef struct {
    bool ack;
    artie_can_frame_priority_rtacp_t priority;
    uint8_t source_address;
    uint8_t target_address;
    uint8_t nbytes;
    uint8_t data[...];
    ...;
} artie_can_frame_rtacp_t;

artie_can_error_t artie_can_init_context_rtacp(artie_can_context_t *ctx, uint8_t source_address);
artie_can_error_t artie_can_rtacp_init_frame(artie_can_frame_t *out, const artie_can_frame_rtacp_t *in);
artie_can_error_t artie_can_rtacp_parse_frame(const artie_can_frame_t *in, artie_can_frame_rtacp_t *out);
artie_can_error_t artie_can_rtacp_send(artie_can_backend_t *handle, const artie_can_frame_t *frame);
bool artie_can_rtacp_is_busy(artie_can_backend_t *handle);

/* -------------------------------------------------------------- psacp.h */

#define ARTIE_CAN_PSACP_HIGH_PROTOCOL_ID ...
#define ARTIE_CAN_PSACP_LOW_PROTOCOL_ID ...
#define ARTIE_CAN_PSACP_MAX_DATA_BYTES ...
#define ARTIE_CAN_PSACP_TOPIC_BROADCAST ...
#define ARTIE_CAN_PSACP_MAX_SUBSCRIPTIONS ...

typedef enum {
    ARTIE_CAN_FRAME_PRIORITY_PSACP_LOW,
    ARTIE_CAN_FRAME_PRIORITY_PSACP_MEDIUM_LOW,
    ARTIE_CAN_FRAME_PRIORITY_PSACP_MEDIUM_HIGH,
    ARTIE_CAN_FRAME_PRIORITY_PSACP_HIGH,
    ...
} artie_can_frame_priority_psacp_t;

typedef struct {
    bool high_priority;
    artie_can_frame_priority_psacp_t priority;
    uint8_t source_address;
    uint8_t topic;
    uint8_t nbytes;
    uint8_t data[...];
    ...;
} artie_can_frame_psacp_t;

artie_can_error_t artie_can_init_context_psacp(artie_can_context_t *ctx, uint8_t node_address);
artie_can_error_t artie_can_psacp_subscribe(artie_can_context_t *ctx, uint8_t topic);
artie_can_error_t artie_can_psacp_unsubscribe(artie_can_context_t *ctx, uint8_t topic);
artie_can_error_t artie_can_psacp_init_frame(artie_can_frame_t *out, const artie_can_frame_psacp_t *in);
artie_can_error_t artie_can_psacp_parse_frame(const artie_can_frame_t *in, artie_can_frame_psacp_t *out);
artie_can_error_t artie_can_psacp_publish(artie_can_backend_t *handle, const artie_can_frame_t *frame);

/* -------------------------------------------------------------- bwacp.h */

#define ARTIE_CAN_BWACP_PROTOCOL_ID ...
#define ARTIE_CAN_BWACP_MULTICAST_ADDRESS ...
#define ARTIE_CAN_BWACP_DEFAULT_BUFFER_SIZE ...
#define ARTIE_CAN_BWACP_TIMEOUT_MS ...

typedef enum {
    ARTIE_CAN_FRAME_PRIORITY_BWACP_LOW,
    ARTIE_CAN_FRAME_PRIORITY_BWACP_MEDIUM,
    ARTIE_CAN_FRAME_PRIORITY_BWACP_HIGH,
    ARTIE_CAN_FRAME_PRIORITY_BWACP_HIGHEST,
    ...
} artie_can_frame_priority_bwacp_t;

typedef enum {
    ARTIE_CAN_BWACP_CLASS_SBC,
    ARTIE_CAN_BWACP_CLASS_MCU,
    ARTIE_CAN_BWACP_CLASS_SENSOR,
    ARTIE_CAN_BWACP_CLASS_MOTOR,
    ...
} artie_can_bwacp_class_t;

artie_can_error_t artie_can_init_context_bwacp(artie_can_context_t *context, uint8_t node_address,
                                               uint8_t node_class);
artie_can_error_t artie_can_bwacp_set_receive_buffer(artie_can_context_t *context, uint8_t *buffer,
                                                     uint32_t buffer_size);
artie_can_error_t artie_can_bwacp_send(artie_can_backend_t *handle, const uint8_t *payload,
                                       uint32_t payload_size, uint32_t address,
                                       uint8_t target_address, uint8_t target_class,
                                       artie_can_frame_priority_bwacp_t priority);
bool artie_can_bwacp_is_busy(artie_can_backend_t *handle);

/* ------------------------------------------------------------- rpcacp.h */

#define ARTIE_CAN_RPCACP_PROTOCOL_ID ...
#define ARTIE_CAN_RPCACP_MAX_PARAMS ...
#define ARTIE_CAN_RPCACP_MAX_REGISTERED_PROCEDURES ...
#define ARTIE_CAN_RPCACP_MAX_NAME_LENGTH ...
#define ARTIE_CAN_RPCACP_MAX_PAYLOAD_SIZE ...
#define ARTIE_CAN_RPCACP_RESERVED_ID_MAX ...
#define ARTIE_CAN_RPCACP_LIST_PAGE_SIZE ...
#define ARTIE_CAN_RPCACP_LIST_PAGE_COUNT ...
#define ARTIE_CAN_RPCACP_RESPONSE_TIMEOUT_MS ...

#define ARTIE_CAN_RPC_ID_WHOAMI ...
#define ARTIE_CAN_RPC_ID_STATUS ...
#define ARTIE_CAN_RPC_ID_LIST ...

#define ARTIE_CAN_RPCACP_ERRNO_TRANSMISSION ...
#define ARTIE_CAN_RPCACP_ERRNO_EPERM ...
#define ARTIE_CAN_RPCACP_ERRNO_E2BIG ...
#define ARTIE_CAN_RPCACP_ERRNO_ENOEXEC ...
#define ARTIE_CAN_RPCACP_ERRNO_EAGAIN ...
#define ARTIE_CAN_RPCACP_ERRNO_EINVAL ...
#define ARTIE_CAN_RPCACP_ERRNO_EALREADY ...

typedef struct {
    char *type_name;
    uint8_t offset_in_msgpack;
    bool optional;
    ...;
} artie_can_rpc_param_descriptor_t;

typedef void *(*artie_can_rpc_function_t)(const void **params, uint8_t param_count,
                                          void *return_buffer, size_t return_buffer_size);

typedef struct {
    uint16_t procedure_id;
    char *name;
    bool synchronous;
    uint8_t param_count;
    artie_can_rpc_param_descriptor_t params[...];
    artie_can_rpc_function_t function;
    artie_can_rpc_param_descriptor_t *return_descriptor;
    uint32_t return_size;
    ...;
} artie_can_rpc_signature_t;

typedef struct {
    const void *data;
    uint32_t size;
    ...;
} artie_can_rpc_value_t;

typedef struct {
    char *node_name;
    uint8_t node_address;
    char *fw_version;
    ...;
} artie_can_whoami_response_t;

typedef struct {
    uint64_t uptime_ms;
    uint32_t err_flags;
    ...;
} artie_can_status_response_t;

artie_can_error_t artie_can_init_context_rpcacp(artie_can_context_t *context, uint8_t node_address,
                                                uint8_t node_class, const char *node_name,
                                                const char *fw_version);
artie_can_error_t artie_can_rpcacp_set_status_err_flags(artie_can_context_t *context, uint32_t err_flags);
artie_can_error_t artie_can_rpcacp_register_procedure(artie_can_backend_t *handle,
                                                      const artie_can_rpc_signature_t *signature);
artie_can_error_t artie_can_rpcacp_call(artie_can_backend_t *handle, uint8_t target_address,
                                        const artie_can_rpc_signature_t *signature,
                                        const artie_can_rpc_value_t *args, uint8_t arg_count);
artie_can_error_t artie_can_rpcacp_get_last_error(artie_can_backend_t *handle, uint8_t *out_errno);
artie_can_error_t artie_can_rpcacp_get_result(artie_can_backend_t *handle,
                                              const artie_can_rpc_signature_t *signature,
                                              void *out, uint32_t out_size);
artie_can_error_t artie_can_rpcacp_get_whoami_result(artie_can_backend_t *handle,
                                                     artie_can_whoami_response_t *out);
artie_can_error_t artie_can_rpcacp_get_status_result(artie_can_backend_t *handle,
                                                     artie_can_status_response_t *out);
artie_can_error_t artie_can_rpcacp_get_list_result(artie_can_backend_t *handle,
                                                   artie_can_rpc_signature_t *out);
bool artie_can_rpcacp_is_busy(artie_can_backend_t *handle);
bool artie_can_rpcacp_is_node_busy(artie_can_backend_t *handle, uint8_t node_address);

/* ------------------------------------------- helpers defined in SOURCE */

uint64_t artie_can_py_monotonic_ms(void);
"""

# The library asks the caller for a monotonic millisecond clock, and calls it from its receiver
# thread on every frame. Answering that from Python would mean acquiring the GIL in the middle of
# the receive path, so the clock is implemented here in C instead and handed to artie_can_init()
# as a plain function pointer.
SOURCE = r"""
#include "artie_can.h"

#ifdef _WIN32
#include <windows.h>
#else
#include <time.h>
#endif

uint64_t artie_can_py_monotonic_ms(void)
{
#ifdef _WIN32
    return (uint64_t)GetTickCount64();
#else
    struct timespec ts;
    (void)clock_gettime(CLOCK_MONOTONIC, &ts);
    return ((uint64_t)ts.tv_sec * 1000ULL) + ((uint64_t)ts.tv_nsec / 1000000ULL);
#endif
}
"""


def _platform_kwargs():
    """Mirror link_artie_can_platform_libs() from CMakeLists.txt."""
    if sys.platform == "win32":
        return {
            "libraries": ["ws2_32"],
            # strncpy and friends; the CMake build silences the same warnings.
            "define_macros": [("_CRT_SECURE_NO_WARNINGS", "1")],
        }
    return {"libraries": ["pthread", "m"], "define_macros": []}


def make_ffi(absolute_paths: bool = False) -> FFI:
    """Build the FFI.

    :param absolute_paths: Whether to give the compiler absolute paths to the C sources and
        headers. setuptools rejects those outright, so the builder it consumes uses relative ones
        and relies on being invoked from this directory; a standalone build that compiles into its
        own output directory changes the working directory and so needs absolute ones.
    """
    def resolve(paths):
        return [str(HERE / path) for path in paths] if absolute_paths else list(paths)

    ffi = FFI()
    ffi.cdef(CDEF)
    ffi.set_source(
        "artie_can._artie_can",
        SOURCE,
        sources=resolve(SOURCES),
        include_dirs=resolve(INCLUDE_DIRS),
        **_platform_kwargs(),
    )
    return ffi


#: What setup.py's `cffi_modules` points at.
ffibuilder = make_ffi()

#: Where a standalone run of this script puts its output, so it stays out of the source tree.
BUILD_DIR = HERE / "build-python"


if __name__ == "__main__":
    # A quick way to check that the declarations above still compile against the headers, without
    # going through pip. To actually use the bindings, install the package instead
    # (`pip install -e .`), which puts the extension where `import artie_can` can find it.
    os.makedirs(BUILD_DIR, exist_ok=True)
    print("built:", make_ffi(absolute_paths=True).compile(tmpdir=str(BUILD_DIR), verbose=True))
