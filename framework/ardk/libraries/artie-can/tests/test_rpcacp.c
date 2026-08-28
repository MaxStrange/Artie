/**
 * @file test_rpcacp.c
 * @brief Test the RPCACP (Remote Procedure Call Artie CAN Protocol) implementation.
 * Uses UDP Multicast backend.
 *
 * Four nodes are set up on the same multicast group. Node 1 acts as the requesting node in all
 * tests; nodes 2-4 act as remote nodes that register procedures and service requests. Since all
 * nodes run in a single thread (driven by _run_event_loops()), registered procedures execute
 * inline during the remote node's tick.
 */

#include <string.h>
#include <time.h>
#include "unity.h"
#include "artie_can.h"
#include "backend_udp_mcast.h"
#include "util.h"

// Platform-specific includes for sleep
#ifdef _WIN32
    #include <windows.h>
    #define SLEEP_MS(ms) Sleep(ms)
#else
    #include <unistd.h>
    #define SLEEP_MS(ms) usleep((ms) * 1000)
#endif

// Default timeout for waiting on an RPC call to complete in tests (in milliseconds)
#define DEFAULT_TIMEOUT_MS 3000

// Extra event loop iterations run after a call completes so the remote node can finish
// processing the final ACK of the exchange before the test moves on.
#define SETTLE_ITERATIONS 5

// Node addresses
#define NODE1_ADDRESS 0x01U
#define NODE2_ADDRESS 0x02U
#define NODE3_ADDRESS 0x03U
#define NODE4_ADDRESS 0x04U

// Multicast configuration for all test nodes
// Each test process gets its own multicast group, so two runs on one host - two CI jobs on
// Docker's shared default bridge, or a developer running this while a job runs - do not end
// up sharing a simulated bus. See test_multicast_group() in util.c.
static char _multicast_group_buffer[16];
static const char *multicast_group = NULL; // set in main() via test_multicast_group(), suite 4
static const uint16_t multicast_port = 7000;

static artie_can_context_t _node1_context;
static artie_can_context_t _node2_context;
static artie_can_context_t _node3_context;
static artie_can_context_t _node4_context;

static artie_can_backend_t _node1;
static artie_can_backend_t _node2;
static artie_can_backend_t _node3;
static artie_can_backend_t _node4;

static artie_can_udp_mcast_context_t _node1_udp_mcast_context;
static artie_can_udp_mcast_context_t _node2_udp_mcast_context;
static artie_can_udp_mcast_context_t _node3_udp_mcast_context;
static artie_can_udp_mcast_context_t _node4_udp_mcast_context;

// Flags recording execution of the registered test procedures (procedures run inline on the
// remote node's tick, so these are set by the time the caller's exchange completes).
static volatile bool _proc_executed = false;
static volatile int _async_exec_count = 0;
static volatile uint8_t _async_last_arg = 0;

/** The callback that node1 uses to receive frames. RPCACP frames are handled internally by the library. */
static void _receive_callback_node1(const artie_can_frame_t *frame)
{
    (void)frame;
}

/** The callback that node2 uses to receive frames. RPCACP frames are handled internally by the library. */
static void _receive_callback_node2(const artie_can_frame_t *frame)
{
    (void)frame;
}

/** The callback that node3 uses to receive frames. RPCACP frames are handled internally by the library. */
static void _receive_callback_node3(const artie_can_frame_t *frame)
{
    (void)frame;
}

/** The callback that node4 uses to receive frames. RPCACP frames are handled internally by the library. */
static void _receive_callback_node4(const artie_can_frame_t *frame)
{
    (void)frame;
}

static void _tick_node(artie_can_backend_t *node, const char *name)
{
    artie_can_error_t err = artie_can_tick(node);
    if (err)
    {
        if (ARTIE_CAN_ERR_ONLY_RETRIABLE(err))
        {
            printf("Retriable error occurred while ticking %s: %d\n", name, err);
        }
        else
        {
            printf("Non-retriable error occurred while ticking %s: %d\n", name, err);
            TEST_FAIL_MESSAGE("Error ticking node");
        }
    }
}

static void _run_event_loops(void)
{
    // Run one tick of the event loop for each node
    _tick_node(&_node1, "node 1");
    _tick_node(&_node2, "node 2");
    _tick_node(&_node3, "node 3");
    _tick_node(&_node4, "node 4");
}

/** Run a few extra event loop iterations to let in-flight frames drain. */
static void _settle(void)
{
    for (int i = 0; i < SETTLE_ITERATIONS; i++)
    {
        _run_event_loops();
        SLEEP_MS(1);
    }
}

/** Drive all event loops until the caller's RPCACP state machine returns to idle. */
static artie_can_error_t _wait_call_complete(artie_can_backend_t *caller)
{
    uint64_t start_time_ms = get_current_time_ms();
    while (artie_can_rpcacp_is_busy(caller))
    {
        if ((get_current_time_ms() - start_time_ms) >= (uint64_t)DEFAULT_TIMEOUT_MS)
        {
            return ARTIE_CAN_ERR_TIMEOUT;
        }
        _run_event_loops();
        SLEEP_MS(1);
    }
    _settle();
    return ARTIE_CAN_ERR_NONE;
}

/** Kick off a call from `caller`, drive all event loops until it completes, and assert on the outcome. */
static void _call_and_expect(artie_can_backend_t *caller, uint8_t target_address, const artie_can_rpc_signature_t *sig,
                              const artie_can_rpc_value_t *args, uint8_t arg_count,
                              artie_can_error_t expected_error, uint8_t expected_errno)
{
    artie_can_error_t err = artie_can_rpcacp_call(caller, target_address, sig, args, arg_count);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    err = _wait_call_complete(caller);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    uint8_t errno_code = 0;
    err = artie_can_rpcacp_get_last_error(caller, &errno_code);
    TEST_ASSERT_EQUAL_INT(expected_error, err);
    TEST_ASSERT_EQUAL_UINT8(expected_errno, errno_code);
}

// ---------------------------------------------------------------------------
// Test procedures (registered on the remote nodes)
// ---------------------------------------------------------------------------

/** Defines a procedure that reads one scalar of the given C type, increments it, and returns it. */
#define DEFINE_ECHO_PROC(suffix, ctype) \
    static void *_proc_echo_##suffix(const void **params, uint8_t param_count, void *return_buffer, size_t return_buffer_size) \
    { \
        (void)param_count; \
        (void)return_buffer_size; \
        ctype value; \
        memcpy(&value, params[0], sizeof(value)); \
        value = (ctype)(value + 1); \
        memcpy(return_buffer, &value, sizeof(value)); \
        return return_buffer; \
    }

DEFINE_ECHO_PROC(u8, uint8_t)
DEFINE_ECHO_PROC(u16, uint16_t)
DEFINE_ECHO_PROC(u32, uint32_t)
DEFINE_ECHO_PROC(u64, uint64_t)
DEFINE_ECHO_PROC(i8, int8_t)
DEFINE_ECHO_PROC(i16, int16_t)
DEFINE_ECHO_PROC(i32, int32_t)
DEFINE_ECHO_PROC(i64, int64_t)
DEFINE_ECHO_PROC(f32, float)
DEFINE_ECHO_PROC(f64, double)

/** A procedure with no parameters and no return value; records that it ran. */
static void *_proc_no_args_no_return(const void **params, uint8_t param_count, void *return_buffer, size_t return_buffer_size)
{
    (void)params;
    (void)param_count;
    (void)return_buffer_size;
    _proc_executed = true;
    return return_buffer;
}

/** Reverses a 4-byte array. */
static void *_proc_reverse_array4(const void **params, uint8_t param_count, void *return_buffer, size_t return_buffer_size)
{
    (void)param_count;
    (void)return_buffer_size;
    const uint8_t *in = (const uint8_t *)params[0];
    uint8_t *out = (uint8_t *)return_buffer;
    for (int i = 0; i < 4; i++)
    {
        out[i] = in[3 - i];
    }
    return return_buffer;
}

// A test struct with no internal padding so its in-memory layout is its wire layout.
typedef struct {
    uint32_t a;
    uint32_t b;
} test_struct_t;

/** Swaps the two members of a test_struct_t. */
static void *_proc_swap_struct(const void **params, uint8_t param_count, void *return_buffer, size_t return_buffer_size)
{
    (void)param_count;
    (void)return_buffer_size;
    test_struct_t s;
    memcpy(&s, params[0], sizeof(s));
    uint32_t tmp = s.a;
    s.a = s.b;
    s.b = tmp;
    memcpy(return_buffer, &s, sizeof(s));
    return return_buffer;
}

// The string echo procedure returns its result in a fixed-size (zero-padded) buffer of this size.
#define STRING_RETURN_SIZE 16U

/** Appends a '!' to the given nul-terminated string. */
static void *_proc_string_excite(const void **params, uint8_t param_count, void *return_buffer, size_t return_buffer_size)
{
    (void)param_count;
    const char *in = (const char *)params[0];
    size_t len = strlen(in);
    if ((len + 2U) > return_buffer_size)
    {
        return NULL;
    }
    memset(return_buffer, 0, STRING_RETURN_SIZE);
    memcpy(return_buffer, in, len);
    ((char *)return_buffer)[len] = '!';
    return return_buffer;
}

/** Sums all of its uint8_t parameters. */
static void *_proc_sum(const void **params, uint8_t param_count, void *return_buffer, size_t return_buffer_size)
{
    (void)return_buffer_size;
    uint8_t sum = 0;
    for (uint8_t i = 0; i < param_count; i++)
    {
        sum = (uint8_t)(sum + *(const uint8_t *)params[i]);
    }
    memcpy(return_buffer, &sum, sizeof(sum));
    return return_buffer;
}

/** An asynchronous procedure; records that it ran and what argument it got. */
static void *_proc_async_notify(const void **params, uint8_t param_count, void *return_buffer, size_t return_buffer_size)
{
    (void)param_count;
    (void)return_buffer_size;
    _async_last_arg = *(const uint8_t *)params[0];
    _async_exec_count = _async_exec_count + 1;
    return return_buffer;
}

// ---------------------------------------------------------------------------
// Signature helpers
// ---------------------------------------------------------------------------

/** Initializes a signature for a synchronous single-parameter echo procedure (same type in and out). */
static void _init_echo_sig(artie_can_rpc_signature_t *sig, artie_can_rpc_param_descriptor_t *return_desc,
                            char *type_name, artie_can_rpc_function_t function, uint32_t return_size)
{
    return_desc->type_name = type_name;
    return_desc->offset_in_msgpack = 0;
    return_desc->optional = false;

    memset(sig, 0, sizeof(*sig));
    sig->procedure_id = 0x10;
    sig->name = "ECHO";
    sig->synchronous = true;
    sig->param_count = 1;
    sig->params[0].type_name = type_name;
    sig->params[0].offset_in_msgpack = 0;
    sig->params[0].optional = false;
    sig->function = function;
    sig->return_descriptor = return_desc;
    sig->return_size = return_size;
}

/** Initializes the signature of the asynchronous notify procedure. */
static void _init_async_sig(artie_can_rpc_signature_t *sig)
{
    memset(sig, 0, sizeof(*sig));
    sig->procedure_id = 0x30;
    sig->name = "ASYNC_NOTIFY";
    sig->synchronous = false;
    sig->param_count = 1;
    sig->params[0].type_name = "uint8_t";
    sig->params[0].offset_in_msgpack = 0;
    sig->params[0].optional = false;
    sig->function = _proc_async_notify;
}

/** Initializes a caller-side signature for one of the standard (reserved) synchronous procedures. */
static void _init_standard_sig(artie_can_rpc_signature_t *sig, uint16_t procedure_id, char *name, uint8_t param_count)
{
    memset(sig, 0, sizeof(*sig));
    sig->procedure_id = procedure_id;
    sig->name = name;
    sig->synchronous = true;
    sig->param_count = param_count;
    if (param_count > 0)
    {
        sig->params[0].type_name = "uint8_t";
        sig->params[0].offset_in_msgpack = 0;
        sig->params[0].optional = false;
    }
}

/**
 * Registers an echo procedure on node 2, calls it from node 1 with the given argument, and
 * asserts that the returned value matches `expected`.
 */
static void _run_echo_test(char *type_name, artie_can_rpc_function_t function,
                            const void *arg, uint32_t arg_size, const void *expected, uint32_t return_size)
{
    artie_can_rpc_param_descriptor_t return_desc;
    artie_can_rpc_signature_t sig;
    _init_echo_sig(&sig, &return_desc, type_name, function, return_size);

    artie_can_error_t err = artie_can_rpcacp_register_procedure(&_node2, &sig);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    artie_can_rpc_value_t args[1];
    args[0].data = arg;
    args[0].size = arg_size;
    _call_and_expect(&_node1, NODE2_ADDRESS, &sig, args, 1, ARTIE_CAN_ERR_NONE, 0);

    uint8_t result[32] = {0};
    err = artie_can_rpcacp_get_result(&_node1, &sig, result, sizeof(result));
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);
    TEST_ASSERT_EQUAL_MEMORY(expected, result, return_size);
}

/**
 * @brief Setup function called before each test.
 */
void setUp(void)
{
    artie_can_error_t err;

    // Reset the procedure execution tracking
    _proc_executed = false;
    _async_exec_count = 0;
    _async_last_arg = 0;

    // Initialize UDP multicast contexts for all nodes
    err = artie_can_init_context_udp_mcast(&_node1_context, &_node1_udp_mcast_context, multicast_group, multicast_port);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    err = artie_can_init_context_udp_mcast(&_node2_context, &_node2_udp_mcast_context, multicast_group, multicast_port);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    err = artie_can_init_context_udp_mcast(&_node3_context, &_node3_udp_mcast_context, multicast_group, multicast_port);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    err = artie_can_init_context_udp_mcast(&_node4_context, &_node4_udp_mcast_context, multicast_group, multicast_port);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    // Set up the nodes to use RPCACP
    err = artie_can_init_context_rpcacp(&_node1_context, NODE1_ADDRESS, 0x01, "node1", "1.0.0");
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    err = artie_can_init_context_rpcacp(&_node2_context, NODE2_ADDRESS, 0x01, "node2", "1.0.0");
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    err = artie_can_init_context_rpcacp(&_node3_context, NODE3_ADDRESS, 0x01, "node3", "1.0.0");
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    err = artie_can_init_context_rpcacp(&_node4_context, NODE4_ADDRESS, 0x01, "node4", "1.0.0");
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    // Initialize backends for all nodes
    err = artie_can_init(&_node1_context, &_node1, ARTIE_CAN_BACKEND_UDP_MCAST, _receive_callback_node1, get_current_time_ms);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    err = artie_can_init(&_node2_context, &_node2, ARTIE_CAN_BACKEND_UDP_MCAST, _receive_callback_node2, get_current_time_ms);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    err = artie_can_init(&_node3_context, &_node3, ARTIE_CAN_BACKEND_UDP_MCAST, _receive_callback_node3, get_current_time_ms);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    err = artie_can_init(&_node4_context, &_node4, ARTIE_CAN_BACKEND_UDP_MCAST, _receive_callback_node4, get_current_time_ms);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);
}

/**
 * @brief Teardown function called after each test.
 */
void tearDown(void)
{
    artie_can_close(&_node1);
    artie_can_close(&_node2);
    artie_can_close(&_node3);
    artie_can_close(&_node4);

    memset(&_node1, 0, sizeof(_node1));
    memset(&_node2, 0, sizeof(_node2));
    memset(&_node3, 0, sizeof(_node3));
    memset(&_node4, 0, sizeof(_node4));
    memset(&_node1_context, 0, sizeof(_node1_context));
    memset(&_node2_context, 0, sizeof(_node2_context));
    memset(&_node3_context, 0, sizeof(_node3_context));
    memset(&_node4_context, 0, sizeof(_node4_context));
    memset(&_node1_udp_mcast_context, 0, sizeof(_node1_udp_mcast_context));
    memset(&_node2_udp_mcast_context, 0, sizeof(_node2_udp_mcast_context));
    memset(&_node3_udp_mcast_context, 0, sizeof(_node3_udp_mcast_context));
    memset(&_node4_udp_mcast_context, 0, sizeof(_node4_udp_mcast_context));
}

/**
 * @brief Test for RPCACP WHOAMI function execution.
 */
void test_rpcacp_whoami_function(void)
{
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");
    printf("!!!!!!!!!!!! Starting test_rpcacp_whoami_function !!!!!!!!!!\n");
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");

    artie_can_rpc_signature_t sig;
    _init_standard_sig(&sig, ARTIE_CAN_RPC_ID_WHOAMI, "WHOAMI", 0);

    _call_and_expect(&_node1, NODE2_ADDRESS, &sig, NULL, 0, ARTIE_CAN_ERR_NONE, 0);

    artie_can_whoami_response_t resp;
    artie_can_error_t err = artie_can_rpcacp_get_whoami_result(&_node1, &resp);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);
    TEST_ASSERT_EQUAL_UINT8(NODE2_ADDRESS, resp.node_address);
    TEST_ASSERT_EQUAL_STRING("node2", resp.node_name);
    TEST_ASSERT_EQUAL_STRING("1.0.0", resp.fw_version);
}

/**
 * @brief Test for RPCACP STATUS function execution.
 */
void test_rpcacp_status_function(void)
{
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");
    printf("!!!!!!!!!!!! Starting test_rpcacp_status_function !!!!!!!!!!\n");
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");

    const uint32_t err_flags = 0xA5A50FF0U;
    artie_can_error_t err = artie_can_rpcacp_set_status_err_flags(&_node2_context, err_flags);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    artie_can_rpc_signature_t sig;
    _init_standard_sig(&sig, ARTIE_CAN_RPC_ID_STATUS, "STATUS", 0);

    _call_and_expect(&_node1, NODE2_ADDRESS, &sig, NULL, 0, ARTIE_CAN_ERR_NONE, 0);

    artie_can_status_response_t resp;
    err = artie_can_rpcacp_get_status_result(&_node1, &resp);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);
    TEST_ASSERT_EQUAL_UINT32(err_flags, resp.err_flags);
    // Uptime should be small (measured from the node's first tick during this test)
    TEST_ASSERT_TRUE(resp.uptime_ms < 60000U);
}

/**
 * @brief Test for RPCACP LIST function execution
 *        and handling of response.
 */
void test_rpcacp_list_function(void)
{
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");
    printf("!!!!!!!!!!!! Starting test_rpcacp_list_function !!!!!!!!!!!\n");
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");

    // Register a device-specific procedure on node 2 so it shows up in the listing (id 0x10 is on page 2)
    artie_can_rpc_param_descriptor_t return_desc;
    artie_can_rpc_signature_t echo_sig;
    _init_echo_sig(&echo_sig, &return_desc, "uint8_t", _proc_echo_u8, sizeof(uint8_t));
    artie_can_error_t err = artie_can_rpcacp_register_procedure(&_node2, &echo_sig);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    artie_can_rpc_signature_t list_sig;
    _init_standard_sig(&list_sig, ARTIE_CAN_RPC_ID_LIST, "LIST", 1);

    // Page 0 holds the standard procedures (ids 0x00-0x07)
    uint8_t page = 0;
    artie_can_rpc_value_t args[1] = {{ &page, sizeof(page) }};
    _call_and_expect(&_node1, NODE2_ADDRESS, &list_sig, args, 1, ARTIE_CAN_ERR_NONE, 0);

    artie_can_rpc_signature_t entries[ARTIE_CAN_RPCACP_LIST_PAGE_SIZE];
    err = artie_can_rpcacp_get_list_result(&_node1, entries);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    TEST_ASSERT_EQUAL_UINT16(ARTIE_CAN_RPC_ID_WHOAMI, entries[0].procedure_id);
    TEST_ASSERT_EQUAL_STRING("WHOAMI", entries[0].name);
    TEST_ASSERT_TRUE(entries[0].synchronous);
    TEST_ASSERT_EQUAL_UINT16(ARTIE_CAN_RPC_ID_STATUS, entries[1].procedure_id);
    TEST_ASSERT_EQUAL_STRING("STATUS", entries[1].name);
    TEST_ASSERT_EQUAL_UINT16(ARTIE_CAN_RPC_ID_LIST, entries[2].procedure_id);
    TEST_ASSERT_EQUAL_STRING("LIST", entries[2].name);
    TEST_ASSERT_EQUAL_UINT8(1, entries[2].param_count);
    TEST_ASSERT_EQUAL_STRING("uint8_t", entries[2].params[0].type_name);
    for (int i = 3; i < (int)ARTIE_CAN_RPCACP_LIST_PAGE_SIZE; i++)
    {
        TEST_ASSERT_EQUAL_UINT16((uint16_t)i, entries[i].procedure_id);
        TEST_ASSERT_EQUAL_STRING(ARTIE_CAN_RPCACP_LIST_UNASSIGNED_NAME, entries[i].name);
    }

    // Page 2 holds ids 0x10-0x17, so the registered procedure should be its first entry
    page = 2;
    _call_and_expect(&_node1, NODE2_ADDRESS, &list_sig, args, 1, ARTIE_CAN_ERR_NONE, 0);

    err = artie_can_rpcacp_get_list_result(&_node1, entries);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    TEST_ASSERT_EQUAL_UINT16(0x10, entries[0].procedure_id);
    TEST_ASSERT_EQUAL_STRING("ECHO", entries[0].name);
    TEST_ASSERT_TRUE(entries[0].synchronous);
    TEST_ASSERT_EQUAL_UINT8(1, entries[0].param_count);
    TEST_ASSERT_EQUAL_STRING("uint8_t", entries[0].params[0].type_name);
    TEST_ASSERT_EQUAL_UINT8(0, entries[0].params[0].offset_in_msgpack);
    TEST_ASSERT_FALSE(entries[0].params[0].optional);
    for (int i = 1; i < (int)ARTIE_CAN_RPCACP_LIST_PAGE_SIZE; i++)
    {
        TEST_ASSERT_EQUAL_UINT16((uint16_t)(0x10 + i), entries[i].procedure_id);
        TEST_ASSERT_EQUAL_STRING(ARTIE_CAN_RPCACP_LIST_UNASSIGNED_NAME, entries[i].name);
    }
}

/**
 * @brief Test for RPCACP function execution with invalid function ID.
 *
 */
void test_rpcacp_invalid_function_id(void)
{
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");
    printf("!!!!!!!!!!!! Starting test_rpcacp_invalid_function_id !!!!!!!!!\n");
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");

    // Node 2 has no procedure registered under this ID, so it should NACK with EPERM
    artie_can_rpc_signature_t sig;
    memset(&sig, 0, sizeof(sig));
    sig.procedure_id = 0x20;
    sig.name = "NOT_REGISTERED";
    sig.synchronous = true;
    sig.param_count = 0;

    _call_and_expect(&_node1, NODE2_ADDRESS, &sig, NULL, 0, ARTIE_CAN_ERR_INVALID_ARG, ARTIE_CAN_RPCACP_ERRNO_EPERM);
}

/**
 * @brief Test for RPCACP function execution with too many parameters.
 *
 */
void test_rpcacp_too_many_parameters(void)
{
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");
    printf("!!!!!!!!!!!! Starting test_rpcacp_too_many_parameters !!!!!!!!!\n");
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");

    // Node 2's registered signature takes a single uint8_t
    artie_can_rpc_param_descriptor_t return_desc;
    artie_can_rpc_signature_t remote_sig;
    _init_echo_sig(&remote_sig, &return_desc, "uint8_t", _proc_echo_u8, sizeof(uint8_t));
    artie_can_error_t err = artie_can_rpcacp_register_procedure(&_node2, &remote_sig);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    // Node 1 calls the same procedure ID with a mismatched signature that packs three uint8_t
    // arguments, which the remote node should reject with E2BIG
    artie_can_rpc_signature_t caller_sig;
    memset(&caller_sig, 0, sizeof(caller_sig));
    caller_sig.procedure_id = remote_sig.procedure_id;
    caller_sig.name = "ECHO_TOO_MANY_ARGS";
    caller_sig.synchronous = true;
    caller_sig.param_count = 3;
    for (uint8_t i = 0; i < caller_sig.param_count; i++)
    {
        caller_sig.params[i].type_name = "uint8_t";
        caller_sig.params[i].offset_in_msgpack = i;
        caller_sig.params[i].optional = false;
    }

    uint8_t vals[3] = {1, 2, 3};
    artie_can_rpc_value_t args[3] = {
        { &vals[0], sizeof(vals[0]) },
        { &vals[1], sizeof(vals[1]) },
        { &vals[2], sizeof(vals[2]) },
    };
    _call_and_expect(&_node1, NODE2_ADDRESS, &caller_sig, args, 3, ARTIE_CAN_ERR_INVALID_ARG, ARTIE_CAN_RPCACP_ERRNO_E2BIG);
}

/**
 * @brief Test for RPCACP function execution with invalid parameters.
 */
void test_rpcacp_invalid_parameters(void)
{
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");
    printf("!!!!!!!!!!!! Starting test_rpcacp_invalid_parameters !!!!!!!!!!!\n");
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");

    // Node 2's registered signature expects a uint32_t (4 wire bytes)
    artie_can_rpc_param_descriptor_t return_desc;
    artie_can_rpc_signature_t remote_sig;
    _init_echo_sig(&remote_sig, &return_desc, "uint32_t", _proc_echo_u32, sizeof(uint32_t));
    artie_can_error_t err = artie_can_rpcacp_register_procedure(&_node2, &remote_sig);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    // Node 1 calls the same procedure ID with a mismatched signature that only packs a single
    // byte, which the remote node should reject with EINVAL
    artie_can_rpc_param_descriptor_t caller_return_desc;
    artie_can_rpc_signature_t caller_sig;
    _init_echo_sig(&caller_sig, &caller_return_desc, "uint8_t", NULL, sizeof(uint8_t));

    uint8_t val = 0x42;
    artie_can_rpc_value_t args[1] = {{ &val, sizeof(val) }};
    _call_and_expect(&_node1, NODE2_ADDRESS, &caller_sig, args, 1, ARTIE_CAN_ERR_INVALID_ARG, ARTIE_CAN_RPCACP_ERRNO_EINVAL);
}

/**
 * @brief Test for RPCACP function execution with asynchronous RPC call.
 *
 */
void test_rpcacp_async_call(void)
{
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");
    printf("!!!!!!!!!!!! Starting test_rpcacp_async_call !!!!!!!!!\n");
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");

    artie_can_rpc_signature_t sig;
    _init_async_sig(&sig);
    artie_can_error_t err = artie_can_rpcacp_register_procedure(&_node2, &sig);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    uint8_t arg = 0x5A;
    artie_can_rpc_value_t args[1] = {{ &arg, sizeof(arg) }};
    _call_and_expect(&_node1, NODE2_ADDRESS, &sig, args, 1, ARTIE_CAN_ERR_NONE, 0);

    // The remote node executed the procedure (inline, before ACKing) and no return value was sent
    TEST_ASSERT_EQUAL_INT(1, _async_exec_count);
    TEST_ASSERT_EQUAL_UINT8(0x5A, _async_last_arg);

    // Node 1 should now believe node 2 is busy with the async procedure
    TEST_ASSERT_TRUE(artie_can_rpcacp_is_node_busy(&_node1, NODE2_ADDRESS));
}

/**
 * @brief Test for RPCACP function execution with asynchronous RPC call
 * followed by attempting the same function call again while still working on it.
 *
 */
void test_rpcacp_async_call_busy_async(void)
{
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");
    printf("!!!!!!!!!!!! Starting test_rpcacp_async_call_busy_async !!!!!!!!!!\n");
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");

    artie_can_rpc_signature_t sig;
    _init_async_sig(&sig);
    artie_can_error_t err = artie_can_rpcacp_register_procedure(&_node2, &sig);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    uint8_t arg = 0x11;
    artie_can_rpc_value_t args[1] = {{ &arg, sizeof(arg) }};
    err = artie_can_rpcacp_call(&_node1, NODE2_ADDRESS, &sig, args, 1);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);
    TEST_ASSERT_TRUE(artie_can_rpcacp_is_busy(&_node1));

    // A node may only drive one RPC exchange at a time, so attempting the same call again while
    // the first is still in flight must be rejected
    err = artie_can_rpcacp_call(&_node1, NODE2_ADDRESS, &sig, args, 1);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_SEND_BUSY, err);

    // The original call should still complete successfully
    err = _wait_call_complete(&_node1);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);
    uint8_t errno_code = 0;
    err = artie_can_rpcacp_get_last_error(&_node1, &errno_code);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);
    TEST_ASSERT_EQUAL_INT(1, _async_exec_count);
}

/**
 * @brief Test for RPCACP function execution with asynchronous RPC call
 * followed by attempting a synchronous call to the same node while still working on it.
 *
 */
void test_rpcacp_async_call_busy_sync(void)
{
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");
    printf("!!!!!!!!!!!! Starting test_rpcacp_async_call_busy_sync !!!!!!!!!!\n");
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");

    artie_can_rpc_signature_t async_sig;
    _init_async_sig(&async_sig);
    artie_can_error_t err = artie_can_rpcacp_register_procedure(&_node2, &async_sig);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    uint8_t arg = 0x22;
    artie_can_rpc_value_t args[1] = {{ &arg, sizeof(arg) }};
    err = artie_can_rpcacp_call(&_node1, NODE2_ADDRESS, &async_sig, args, 1);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    // While the async exchange is in flight, a synchronous call must be rejected
    artie_can_rpc_signature_t whoami_sig;
    _init_standard_sig(&whoami_sig, ARTIE_CAN_RPC_ID_WHOAMI, "WHOAMI", 0);
    err = artie_can_rpcacp_call(&_node1, NODE2_ADDRESS, &whoami_sig, NULL, 0);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_SEND_BUSY, err);

    // Let the async call complete; node 2 is then believed busy with the async procedure
    err = _wait_call_complete(&_node1);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);
    uint8_t errno_code = 0;
    err = artie_can_rpcacp_get_last_error(&_node1, &errno_code);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);
    TEST_ASSERT_TRUE(artie_can_rpcacp_is_node_busy(&_node1, NODE2_ADDRESS));

    // A subsequent synchronous call succeeds, and node 2 accepting it clears the busy belief
    _call_and_expect(&_node1, NODE2_ADDRESS, &whoami_sig, NULL, 0, ARTIE_CAN_ERR_NONE, 0);
    TEST_ASSERT_FALSE(artie_can_rpcacp_is_node_busy(&_node1, NODE2_ADDRESS));
}

/**
 * @brief Test for RPCACP function execution with asynchronous RPC call
 * on several nodes.
 *
 */
void test_rpcacp_async_call_multiple_nodes(void)
{
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");
    printf("!!!!!!!!!!!! Starting test_rpcacp_async_call_multiple_nodes !!!!!!!!!!\n");
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");

    artie_can_rpc_signature_t sig;
    _init_async_sig(&sig);

    artie_can_error_t err = artie_can_rpcacp_register_procedure(&_node2, &sig);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);
    err = artie_can_rpcacp_register_procedure(&_node3, &sig);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);
    err = artie_can_rpcacp_register_procedure(&_node4, &sig);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    uint8_t targets[3] = {NODE2_ADDRESS, NODE3_ADDRESS, NODE4_ADDRESS};
    for (int i = 0; i < 3; i++)
    {
        uint8_t arg = targets[i];
        artie_can_rpc_value_t args[1] = {{ &arg, sizeof(arg) }};
        _call_and_expect(&_node1, targets[i], &sig, args, 1, ARTIE_CAN_ERR_NONE, 0);
        TEST_ASSERT_EQUAL_INT(i + 1, _async_exec_count);
        TEST_ASSERT_EQUAL_UINT8(targets[i], _async_last_arg);
    }

    // Node 1 may have one pending async call per remote node, and should believe all three are busy
    TEST_ASSERT_TRUE(artie_can_rpcacp_is_node_busy(&_node1, NODE2_ADDRESS));
    TEST_ASSERT_TRUE(artie_can_rpcacp_is_node_busy(&_node1, NODE3_ADDRESS));
    TEST_ASSERT_TRUE(artie_can_rpcacp_is_node_busy(&_node1, NODE4_ADDRESS));
}

/**
 * @brief Test for RPCACP function that takes no args and returns no data.
 *
 */
void test_rpcacp_no_args_no_return(void)
{
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");
    printf("!!!!!!!!!!!! Starting test_rpcacp_no_args_no_return !!!!!!!!!!\n");
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");

    artie_can_rpc_signature_t sig;
    memset(&sig, 0, sizeof(sig));
    sig.procedure_id = 0x40;
    sig.name = "NO_ARGS_NO_RETURN";
    sig.synchronous = true;
    sig.param_count = 0;
    sig.function = _proc_no_args_no_return;

    artie_can_error_t err = artie_can_rpcacp_register_procedure(&_node2, &sig);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    _call_and_expect(&_node1, NODE2_ADDRESS, &sig, NULL, 0, ARTIE_CAN_ERR_NONE, 0);
    TEST_ASSERT_TRUE(_proc_executed);

    // The procedure has no return value, so asking for one is an error
    uint8_t result[8];
    err = artie_can_rpcacp_get_result(&_node1, &sig, result, sizeof(result));
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_INVALID_ARG, err);
}

/**
 * @brief Scalar type uint8_t
 */
void test_rpcacp_uint8_args_uint8_return(void)
{
    printf("!!!!!!!!!! Starting test_rpcacp_uint8_args_uint8_return !!!!!!!!!!\n");
    uint8_t arg = 41;
    uint8_t expected = 42;
    _run_echo_test("uint8_t", _proc_echo_u8, &arg, sizeof(arg), &expected, sizeof(expected));
}

/**
 * @brief Scalar type uint16_t
 */
void test_rpcacp_uint16_args_uint16_return(void)
{
    printf("!!!!!!!!!! Starting test_rpcacp_uint16_args_uint16_return !!!!!!!!!!\n");
    uint16_t arg = 0xBEEE;
    uint16_t expected = 0xBEEF;
    _run_echo_test("uint16_t", _proc_echo_u16, &arg, sizeof(arg), &expected, sizeof(expected));
}

/**
 * @brief Scalar type uint32_t
 */
void test_rpcacp_uint32_args_uint32_return(void)
{
    printf("!!!!!!!!!! Starting test_rpcacp_uint32_args_uint32_return !!!!!!!!!!\n");
    uint32_t arg = 0xDEADBEEEUL;
    uint32_t expected = 0xDEADBEEFUL;
    _run_echo_test("uint32_t", _proc_echo_u32, &arg, sizeof(arg), &expected, sizeof(expected));
}

/**
 * @brief Scalar type uint64_t
 */
void test_rpcacp_uint64_args_uint64_return(void)
{
    printf("!!!!!!!!!! Starting test_rpcacp_uint64_args_uint64_return !!!!!!!!!!\n");
    uint64_t arg = 0x1122334455667788ULL;
    uint64_t expected = 0x1122334455667789ULL;
    _run_echo_test("uint64_t", _proc_echo_u64, &arg, sizeof(arg), &expected, sizeof(expected));
}

/**
 * @brief Scalar type int8_t
 */
void test_rpcacp_int8_args_int8_return(void)
{
    printf("!!!!!!!!!! Starting test_rpcacp_int8_args_int8_return !!!!!!!!!!\n");
    int8_t arg = -5;
    int8_t expected = -4;
    _run_echo_test("int8_t", _proc_echo_i8, &arg, sizeof(arg), &expected, sizeof(expected));
}

/**
 * @brief Scalar type int16_t
 */
void test_rpcacp_int16_args_int16_return(void)
{
    printf("!!!!!!!!!! Starting test_rpcacp_int16_args_int16_return !!!!!!!!!!\n");
    int16_t arg = -1000;
    int16_t expected = -999;
    _run_echo_test("int16_t", _proc_echo_i16, &arg, sizeof(arg), &expected, sizeof(expected));
}

/**
 * @brief Scalar type int32_t
 */
void test_rpcacp_int32_args_int32_return(void)
{
    printf("!!!!!!!!!! Starting test_rpcacp_int32_args_int32_return !!!!!!!!!!\n");
    int32_t arg = -123457;
    int32_t expected = -123456;
    _run_echo_test("int32_t", _proc_echo_i32, &arg, sizeof(arg), &expected, sizeof(expected));
}

/**
 * @brief Scalar type int64_t
 */
void test_rpcacp_int64_args_int64_return(void)
{
    printf("!!!!!!!!!! Starting test_rpcacp_int64_args_int64_return !!!!!!!!!!\n");
    int64_t arg = -9876543210LL;
    int64_t expected = -9876543209LL;
    _run_echo_test("int64_t", _proc_echo_i64, &arg, sizeof(arg), &expected, sizeof(expected));
}

/**
 * @brief Scalar type float
 */
void test_rpcacp_float_args_float_return(void)
{
    printf("!!!!!!!!!! Starting test_rpcacp_float_args_float_return !!!!!!!!!!\n");
    // 1.5 and 2.5 are exactly representable in the 16-bit wire format
    float arg = 1.5f;
    float expected = 2.5f;
    _run_echo_test("float", _proc_echo_f32, &arg, sizeof(arg), &expected, sizeof(expected));
}

/**
 * @brief Scalar type double
 */
void test_rpcacp_double_args_double_return(void)
{
    printf("!!!!!!!!!! Starting test_rpcacp_double_args_double_return !!!!!!!!!!\n");
    // 1.5 and 2.5 are exactly representable in the 32-bit wire format
    double arg = 1.5;
    double expected = 2.5;
    _run_echo_test("double", _proc_echo_f64, &arg, sizeof(arg), &expected, sizeof(expected));
}

/**
 * @brief Complex type array
 */
void test_rpcacp_array_args_array_return(void)
{
    printf("!!!!!!!!!! Starting test_rpcacp_array_args_array_return !!!!!!!!!!\n");
    uint8_t arg[4] = {1, 2, 3, 4};
    uint8_t expected[4] = {4, 3, 2, 1};
    _run_echo_test("array<uint8_t, 4>", _proc_reverse_array4, arg, sizeof(arg), expected, sizeof(expected));
}

/**
 * @brief Complex type struct
 */
void test_rpcacp_struct_args_struct_return(void)
{
    printf("!!!!!!!!!! Starting test_rpcacp_struct_args_struct_return !!!!!!!!!!\n");
    test_struct_t arg = { .a = 0x11111111UL, .b = 0x22222222UL };
    test_struct_t expected = { .a = 0x22222222UL, .b = 0x11111111UL };
    _run_echo_test("struct test_struct_t", _proc_swap_struct, &arg, sizeof(arg), &expected, sizeof(expected));
}

/**
 * @brief Complex type string
 */
void test_rpcacp_string_args_string_return(void)
{
    printf("!!!!!!!!!! Starting test_rpcacp_string_args_string_return !!!!!!!!!!\n");
    const char *arg = "hello";
    char expected[STRING_RETURN_SIZE] = "hello!"; // remainder zero-filled, matching the procedure's padding
    _run_echo_test("string", _proc_string_excite, arg, (uint32_t)strlen(arg) + 1U, expected, STRING_RETURN_SIZE);
}

/**
 * @brief RPCACP call with 15 parameters.
 */
void test_rpcacp_15_parameters(void)
{
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");
    printf("!!!!!!!!!!!! Starting test_rpcacp_15_parameters !!!!!!!!!!!\n");
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");

    artie_can_rpc_param_descriptor_t return_desc = { "uint8_t", 0, false };
    artie_can_rpc_signature_t sig;
    memset(&sig, 0, sizeof(sig));
    sig.procedure_id = 0x50;
    sig.name = "SUM15";
    sig.synchronous = true;
    sig.param_count = ARTIE_CAN_RPCACP_MAX_PARAMS;
    for (uint8_t i = 0; i < sig.param_count; i++)
    {
        sig.params[i].type_name = "uint8_t";
        sig.params[i].offset_in_msgpack = i;
        sig.params[i].optional = false;
    }
    sig.function = _proc_sum;
    sig.return_descriptor = &return_desc;
    sig.return_size = sizeof(uint8_t);

    artie_can_error_t err = artie_can_rpcacp_register_procedure(&_node2, &sig);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    uint8_t vals[ARTIE_CAN_RPCACP_MAX_PARAMS];
    artie_can_rpc_value_t args[ARTIE_CAN_RPCACP_MAX_PARAMS];
    uint8_t expected_sum = 0;
    for (uint8_t i = 0; i < ARTIE_CAN_RPCACP_MAX_PARAMS; i++)
    {
        vals[i] = (uint8_t)(i + 1U);
        expected_sum = (uint8_t)(expected_sum + vals[i]);
        args[i].data = &vals[i];
        args[i].size = sizeof(vals[i]);
    }

    _call_and_expect(&_node1, NODE2_ADDRESS, &sig, args, ARTIE_CAN_RPCACP_MAX_PARAMS, ARTIE_CAN_ERR_NONE, 0);

    uint8_t result = 0;
    err = artie_can_rpcacp_get_result(&_node1, &sig, &result, sizeof(result));
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);
    TEST_ASSERT_EQUAL_UINT8(expected_sum, result);
}


int main(void)
{
    multicast_group = test_multicast_group(_multicast_group_buffer, sizeof(_multicast_group_buffer), 4);
    // Printed so a CI log says which bus this run used; the group is per-process, so it is
    // the first thing worth knowing if a run ever does look like it heard someone else.
    printf("Test bus: %s:%u\n", multicast_group, (unsigned int)multicast_port);

    UNITY_BEGIN();

    RUN_TEST(test_rpcacp_whoami_function);
    RUN_TEST(test_rpcacp_status_function);
    RUN_TEST(test_rpcacp_list_function);
    RUN_TEST(test_rpcacp_invalid_function_id);
    RUN_TEST(test_rpcacp_too_many_parameters);
    RUN_TEST(test_rpcacp_invalid_parameters);
    RUN_TEST(test_rpcacp_no_args_no_return);
    RUN_TEST(test_rpcacp_uint8_args_uint8_return);
    RUN_TEST(test_rpcacp_uint16_args_uint16_return);
    RUN_TEST(test_rpcacp_uint32_args_uint32_return);
    RUN_TEST(test_rpcacp_uint64_args_uint64_return);
    RUN_TEST(test_rpcacp_int8_args_int8_return);
    RUN_TEST(test_rpcacp_int16_args_int16_return);
    RUN_TEST(test_rpcacp_int32_args_int32_return);
    RUN_TEST(test_rpcacp_int64_args_int64_return);
    RUN_TEST(test_rpcacp_float_args_float_return);
    RUN_TEST(test_rpcacp_double_args_double_return);
    RUN_TEST(test_rpcacp_array_args_array_return);
    RUN_TEST(test_rpcacp_struct_args_struct_return);
    RUN_TEST(test_rpcacp_string_args_string_return);
    RUN_TEST(test_rpcacp_async_call);
    RUN_TEST(test_rpcacp_async_call_busy_async);
    RUN_TEST(test_rpcacp_async_call_busy_sync);
    RUN_TEST(test_rpcacp_async_call_multiple_nodes);
    RUN_TEST(test_rpcacp_15_parameters);

    return UNITY_END();
}
