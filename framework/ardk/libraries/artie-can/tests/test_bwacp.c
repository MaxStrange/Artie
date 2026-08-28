/**
 * @file test_bwacp.c
 * @brief Test the BWACP (Block Write Artie CAN Protocol) implementation.
 * Uses UDP Multicast backend.
 */

#include <stdlib.h>
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

// Default timeout for receive calls in tests (in milliseconds)
#define DEFAULT_TIMEOUT_MS ((uint32_t)(1.25 * ARTIE_CAN_BWACP_TIMEOUT_MS))

// Size of receive buffers for BWACP tests
#define RECEIVE_BUFFER_SIZE 65536

// Multicast configuration for all test nodes
// Each test process gets its own multicast group, so two runs on one host - two CI jobs on
// Docker's shared default bridge, or a developer running this while a job runs - do not end
// up sharing a simulated bus. See test_multicast_group() in util.c.
static char _multicast_group_buffer[16];
static const char *multicast_group = NULL; // set in main() via test_multicast_group(), suite 2
static const uint16_t multicast_port = 6000;

static artie_can_context_t _node1_context;
static artie_can_context_t _node2_context;
static artie_can_context_t _node3_context;
static artie_can_context_t _node4_context; // Only used in test_concurrent_bwacp
static artie_can_backend_t _node1;
static artie_can_backend_t _node2;
static artie_can_backend_t _node3;
static artie_can_backend_t _node4; // Only used in test_concurrent_bwacp
static artie_can_udp_mcast_context_t _node1_udp_mcast_context;
static artie_can_udp_mcast_context_t _node2_udp_mcast_context;
static artie_can_udp_mcast_context_t _node3_udp_mcast_context;
static artie_can_udp_mcast_context_t _node4_udp_mcast_context; // Only used in test_concurrent_bwacp

// Receive buffers for BWACP
static uint8_t _node1_receive_buffer[RECEIVE_BUFFER_SIZE];
static uint8_t _node2_receive_buffer[RECEIVE_BUFFER_SIZE];
static uint8_t _node3_receive_buffer[RECEIVE_BUFFER_SIZE];
static uint8_t _node4_receive_buffer[RECEIVE_BUFFER_SIZE]; // Only used in test_concurrent_bwacp

// RTACP tracking for test_rtacp_while_bwacp
static volatile bool _rtacp_callback_called1 = false;
static volatile bool _rtacp_callback_called2 = false;
static volatile bool _rtacp_callback_called3 = false;
static volatile artie_can_frame_rtacp_t _rtacp_frame_received_in_callback1;
static volatile artie_can_frame_rtacp_t _rtacp_frame_received_in_callback2;
static volatile artie_can_frame_rtacp_t _rtacp_frame_received_in_callback3;

static void _run_event_loops(void)
{
    // Run one tick of the event loop for each node
    artie_can_error_t err;
    err = artie_can_tick(&_node1);
    if (err != ARTIE_CAN_ERR_NONE)
    {
        printf("Error ticking node 1: %d\n", err);
        TEST_FAIL_MESSAGE("Error ticking node 1");
    }

    err = artie_can_tick(&_node2);
    if (err != ARTIE_CAN_ERR_NONE)
    {
        printf("Error ticking node 2: %d\n", err);
        TEST_FAIL_MESSAGE("Error ticking node 2");
    }

    err = artie_can_tick(&_node3);
    if (err != ARTIE_CAN_ERR_NONE)
    {
        printf("Error ticking node 3: %d\n", err);
        TEST_FAIL_MESSAGE("Error ticking node 3");
    }

    if (_node4.context != NULL) // Only tick node 4 if it has been initialized (used in test_concurrent_bwacp)
    {
        err = artie_can_tick(&_node4);
        if (err != ARTIE_CAN_ERR_NONE)
        {
            printf("Error ticking node 4: %d\n", err);
            TEST_FAIL_MESSAGE("Error ticking node 4");
        }
    }
}

static void _empty_rx_callback(const artie_can_frame_t *frame)
{
    // Do nothing - we will check the receive buffers directly in the tests
}

/** The callback that node1 uses to receive frames. */
static void _receive_callback_node1(const artie_can_frame_t *frame)
{
    // For BWACP, data is written directly to the receive buffer.
    // For RTACP, we need to parse and store the frame in the callback.
    artie_can_frame_rtacp_t rtacp_frame;
    artie_can_error_t err = artie_can_rtacp_parse_frame(frame, &rtacp_frame);
    if (err == ARTIE_CAN_ERR_NONE)
    {
        // This is an RTACP frame
        _rtacp_frame_received_in_callback1.ack = rtacp_frame.ack;
        _rtacp_frame_received_in_callback1.priority = rtacp_frame.priority;
        _rtacp_frame_received_in_callback1.source_address = rtacp_frame.source_address;
        _rtacp_frame_received_in_callback1.target_address = rtacp_frame.target_address;
        _rtacp_frame_received_in_callback1.nbytes = rtacp_frame.nbytes;
        for (uint8_t i = 0; i < rtacp_frame.nbytes; i++)
        {
            _rtacp_frame_received_in_callback1.data[i] = rtacp_frame.data[i];
        }
        _rtacp_callback_called1 = true;
    }
    // If not RTACP, it's BWACP and handled internally
}

/** The callback that node2 uses to receive frames. */
static void _receive_callback_node2(const artie_can_frame_t *frame)
{
    // For BWACP, data is written directly to the receive buffer.
    // For RTACP, we need to parse and store the frame in the callback.
    artie_can_frame_rtacp_t rtacp_frame;
    artie_can_error_t err = artie_can_rtacp_parse_frame(frame, &rtacp_frame);
    if (err == ARTIE_CAN_ERR_NONE)
    {
        // This is an RTACP frame
        _rtacp_frame_received_in_callback2.ack = rtacp_frame.ack;
        _rtacp_frame_received_in_callback2.priority = rtacp_frame.priority;
        _rtacp_frame_received_in_callback2.source_address = rtacp_frame.source_address;
        _rtacp_frame_received_in_callback2.target_address = rtacp_frame.target_address;
        _rtacp_frame_received_in_callback2.nbytes = rtacp_frame.nbytes;
        for (uint8_t i = 0; i < rtacp_frame.nbytes; i++)
        {
            _rtacp_frame_received_in_callback2.data[i] = rtacp_frame.data[i];
        }
        _rtacp_callback_called2 = true;
    }
    // If not RTACP, it's BWACP and handled internally
}

/** The callback that node3 uses to receive frames. */
static void _receive_callback_node3(const artie_can_frame_t *frame)
{
    // For BWACP, data is written directly to the receive buffer.
    // For RTACP, we need to parse and store the frame in the callback.
    artie_can_frame_rtacp_t rtacp_frame;
    artie_can_error_t err = artie_can_rtacp_parse_frame(frame, &rtacp_frame);
    if (err == ARTIE_CAN_ERR_NONE)
    {
        // This is an RTACP frame
        _rtacp_frame_received_in_callback3.ack = rtacp_frame.ack;
        _rtacp_frame_received_in_callback3.priority = rtacp_frame.priority;
        _rtacp_frame_received_in_callback3.source_address = rtacp_frame.source_address;
        _rtacp_frame_received_in_callback3.target_address = rtacp_frame.target_address;
        _rtacp_frame_received_in_callback3.nbytes = rtacp_frame.nbytes;
        for (uint8_t i = 0; i < rtacp_frame.nbytes; i++)
        {
            _rtacp_frame_received_in_callback3.data[i] = rtacp_frame.data[i];
        }
        _rtacp_callback_called3 = true;
    }
    // If not RTACP, it's BWACP and handled internally
}

/** Callback for node4, when it is used. */
static void _receive_callback_node4(const artie_can_frame_t *frame)
{
    // Not used
}

/**
 * @brief Setup function called before each test.
 *
 * This function runs before each individual test in this file.
 * Use it to initialize any state needed for your tests.
 *
 * Note that node4 is only used in a subset of tests, so we do not initialize it here.
 */
void setUp(void)
{
    artie_can_error_t err;

    // Clear receive buffers
    memset(_node1_receive_buffer, 0, sizeof(_node1_receive_buffer));
    memset(_node2_receive_buffer, 0, sizeof(_node2_receive_buffer));
    memset(_node3_receive_buffer, 0, sizeof(_node3_receive_buffer));

    // Reset RTACP callback flags
    _rtacp_callback_called1 = false;
    _rtacp_callback_called2 = false;
    _rtacp_callback_called3 = false;

    // Set up the nodes with UDP multicast contexts
    err = artie_can_init_context_udp_mcast(&_node1_context, &_node1_udp_mcast_context, multicast_group, multicast_port);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    err = artie_can_init_context_udp_mcast(&_node2_context, &_node2_udp_mcast_context, multicast_group, multicast_port);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    err = artie_can_init_context_udp_mcast(&_node3_context, &_node3_udp_mcast_context, multicast_group, multicast_port);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    // Set up the nodes to use both RTACP and BWACP
    err = artie_can_init_context_rtacp(&_node1_context, 0x01); // Node 1: Address 0x01
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);
    err = artie_can_init_context_bwacp(&_node1_context, 0x01, ARTIE_CAN_BWACP_CLASS_SBC); // Node 1: SBC
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    err = artie_can_init_context_rtacp(&_node2_context, 0x02); // Node 2: Address 0x02
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);
    err = artie_can_init_context_bwacp(&_node2_context, 0x02, ARTIE_CAN_BWACP_CLASS_SENSOR); // Node 2: Sensor
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    err = artie_can_init_context_rtacp(&_node3_context, 0x03); // Node 3: Address 0x03
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);
    err = artie_can_init_context_bwacp(&_node3_context, 0x03, ARTIE_CAN_BWACP_CLASS_SENSOR); // Node 3: Sensor
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    // Set receive buffers for BWACP
    err = artie_can_bwacp_set_receive_buffer(&_node1_context, _node1_receive_buffer, sizeof(_node1_receive_buffer));
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    err = artie_can_bwacp_set_receive_buffer(&_node2_context, _node2_receive_buffer, sizeof(_node2_receive_buffer));
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    err = artie_can_bwacp_set_receive_buffer(&_node3_context, _node3_receive_buffer, sizeof(_node3_receive_buffer));
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    // Set up the backends for the nodes
    err = artie_can_init(&_node1_context, &_node1, ARTIE_CAN_BACKEND_UDP_MCAST, _receive_callback_node1, get_current_time_ms);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    err = artie_can_init(&_node2_context, &_node2, ARTIE_CAN_BACKEND_UDP_MCAST, _receive_callback_node2, get_current_time_ms);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    err = artie_can_init(&_node3_context, &_node3, ARTIE_CAN_BACKEND_UDP_MCAST, _receive_callback_node3, get_current_time_ms);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);
}

/**
 * @brief Teardown function called after each test.
 *
 * This function runs after each individual test in this file.
 * Use it to clean up any state created during the test.
 */
void tearDown(void)
{
    artie_can_error_t err;

    // Close the backends for the nodes
    err = artie_can_close(&_node1);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    err = artie_can_close(&_node2);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    err = artie_can_close(&_node3);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    artie_can_close(&_node4); // In case it was used in the test; ignore errors since it may not have been initialized

    // Clean up contexts by zeroing them out (not strictly necessary, but good practice since we are reusing them in setUp)
    memset(&_node1, 0, sizeof(_node1));
    memset(&_node2, 0, sizeof(_node2));
    memset(&_node3, 0, sizeof(_node3));
    memset(&_node4, 0, sizeof(_node3));
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
 * @brief Test sending a single byte over the BWACP protocol.
 * Send to two other nodes and verify that they both received the byte successfully.
 *
 */
void test_send_one_byte(void)
{
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");
    printf("!!!!!!!!!!!! Starting test_send_one_byte !!!!!!!!!!!\n");
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");

    artie_can_error_t err;

    // Create a 1-byte payload
    uint8_t send_data[] = {0x42};
    // Address specifies the offset within the receive buffer where data should be written
    uint32_t buffer_offset = 0x1000;

    // Send from node 1 to multicast address targeting SENSOR class (nodes 2 and 3 are sensors)
    err = artie_can_bwacp_send(&_node1, send_data, sizeof(send_data), buffer_offset, ARTIE_CAN_BWACP_MULTICAST_ADDRESS, ARTIE_CAN_BWACP_CLASS_SENSOR, ARTIE_CAN_FRAME_PRIORITY_BWACP_MEDIUM);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    // Run event loops and wait for node 1 to finish sending
    // Node 1 should transition to WAITING_COMPLETE, then back to IDLE after timeout
    bool node1_complete = false;
    uint64_t start_time = get_current_time_ms();
    while (!node1_complete && (get_current_time_ms() - start_time) < DEFAULT_TIMEOUT_MS)
    {
        _run_event_loops();
        SLEEP_MS(1);
        if (!artie_can_bwacp_is_busy(&_node1))
        {
            node1_complete = true;
        }
    }
    TEST_ASSERT_TRUE_MESSAGE(node1_complete, "Node 1 did not complete sending");

    // Check that node 2 received the byte at the correct buffer offset
    TEST_ASSERT_EQUAL_UINT8(0x42, _node2_receive_buffer[buffer_offset]);
    TEST_ASSERT_EQUAL_UINT32(buffer_offset, _node2_context.bwacp_context.receive_address);

    // Check that node 3 received the byte at the correct buffer offset
    TEST_ASSERT_EQUAL_UINT8(0x42, _node3_receive_buffer[buffer_offset]);
    TEST_ASSERT_EQUAL_UINT32(buffer_offset, _node3_context.bwacp_context.receive_address);

    printf("!!!!!!!!!!!! test_send_one_byte PASSED !!!!!!!!!!!!!!\n");
}

/**
 * @brief Same as test_send_one_byte, but sends 4 bytes.
 *
 */
void test_send_four_bytes(void)
{
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");
    printf("!!!!!!!!!!!! Starting test_send_four_bytes !!!!!!!!!!\n");
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");

    artie_can_error_t err;

    // Create a 4-byte payload
    uint8_t send_data[] = {0xDE, 0xAD, 0xBE, 0xEF};
    // Address specifies the offset within the receive buffer where data should be written
    uint32_t buffer_offset = 0x2000;

    // Send from node 1 to multicast address targeting SENSOR class (nodes 2 and 3 are sensors)
    err = artie_can_bwacp_send(&_node1, send_data, sizeof(send_data), buffer_offset, ARTIE_CAN_BWACP_MULTICAST_ADDRESS, ARTIE_CAN_BWACP_CLASS_SENSOR, ARTIE_CAN_FRAME_PRIORITY_BWACP_MEDIUM);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    // Run event loops and wait for node 1 to finish sending
    // Node 1 should transition to WAITING_COMPLETE, then back to IDLE after timeout
    bool node1_complete = false;
    uint64_t start_time = get_current_time_ms();
    while (!node1_complete && (get_current_time_ms() - start_time) < DEFAULT_TIMEOUT_MS)
    {
        _run_event_loops();
        SLEEP_MS(1);
        if (artie_can_bwacp_is_busy(&_node1) == false)
        {
            node1_complete = true;
        }
    }
    TEST_ASSERT_TRUE_MESSAGE(node1_complete, "Node 1 did not complete sending");

    // Check that node 2 received the bytes at the correct buffer offset
    TEST_ASSERT_EQUAL_UINT8(0xDE, _node2_receive_buffer[buffer_offset]);
    TEST_ASSERT_EQUAL_UINT8(0xAD, _node2_receive_buffer[buffer_offset + 1]);
    TEST_ASSERT_EQUAL_UINT8(0xBE, _node2_receive_buffer[buffer_offset + 2]);
    TEST_ASSERT_EQUAL_UINT8(0xEF, _node2_receive_buffer[buffer_offset + 3]);
    TEST_ASSERT_EQUAL_UINT32(buffer_offset, _node2_context.bwacp_context.receive_address);

    // Check that node 3 received the bytes at the correct buffer offset
    TEST_ASSERT_EQUAL_UINT8(0xDE, _node3_receive_buffer[buffer_offset]);
    TEST_ASSERT_EQUAL_UINT8(0xAD, _node3_receive_buffer[buffer_offset + 1]);
    TEST_ASSERT_EQUAL_UINT8(0xBE, _node3_receive_buffer[buffer_offset + 2]);
    TEST_ASSERT_EQUAL_UINT8(0xEF, _node3_receive_buffer[buffer_offset + 3]);
    TEST_ASSERT_EQUAL_UINT32(buffer_offset, _node3_context.bwacp_context.receive_address);

    printf("!!!!!!!!!!!! test_send_four_bytes PASSED !!!!!!!!!!!\n");
}

/**
 * @brief Same as test_send_one_byte, but sends 8 bytes.
 *
 */
void test_send_eight_bytes(void)
{
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");
    printf("!!!!!!!!!!!! Starting test_send_eight_bytes !!!!!!!!!\n");
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");

    artie_can_error_t err;

    // Create an 8-byte payload
    uint8_t send_data[] = {0x01, 0x23, 0x45, 0x67, 0x89, 0xAB, 0xCD, 0xEF};
    // Address specifies the offset within the receive buffer where data should be written
    uint32_t buffer_offset = 0x3000;

    // Send from node 1 to multicast address targeting SENSOR class (nodes 2 and 3 are sensors)
    err = artie_can_bwacp_send(&_node1, send_data, sizeof(send_data), buffer_offset, ARTIE_CAN_BWACP_MULTICAST_ADDRESS, ARTIE_CAN_BWACP_CLASS_SENSOR, ARTIE_CAN_FRAME_PRIORITY_BWACP_MEDIUM);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    // Run event loops and wait for node 1 to finish sending
    // Node 1 should transition to WAITING_COMPLETE, then back to IDLE after timeout
    bool node1_complete = false;
    uint64_t start_time = get_current_time_ms();
    while (!node1_complete && (get_current_time_ms() - start_time) < DEFAULT_TIMEOUT_MS)
    {
        _run_event_loops();
        SLEEP_MS(1);
        if (artie_can_bwacp_is_busy(&_node1) == false)
        {
            node1_complete = true;
        }
    }
    TEST_ASSERT_TRUE_MESSAGE(node1_complete, "Node 1 did not complete sending");

    // Check that node 2 received the bytes at the correct buffer offset
    TEST_ASSERT_EQUAL_UINT8(0x01, _node2_receive_buffer[buffer_offset]);
    TEST_ASSERT_EQUAL_UINT8(0x23, _node2_receive_buffer[buffer_offset + 1]);
    TEST_ASSERT_EQUAL_UINT8(0x45, _node2_receive_buffer[buffer_offset + 2]);
    TEST_ASSERT_EQUAL_UINT8(0x67, _node2_receive_buffer[buffer_offset + 3]);
    TEST_ASSERT_EQUAL_UINT8(0x89, _node2_receive_buffer[buffer_offset + 4]);
    TEST_ASSERT_EQUAL_UINT8(0xAB, _node2_receive_buffer[buffer_offset + 5]);
    TEST_ASSERT_EQUAL_UINT8(0xCD, _node2_receive_buffer[buffer_offset + 6]);
    TEST_ASSERT_EQUAL_UINT8(0xEF, _node2_receive_buffer[buffer_offset + 7]);
    TEST_ASSERT_EQUAL_UINT32(buffer_offset, _node2_context.bwacp_context.receive_address);

    // Check that node 3 received the bytes at the correct buffer offset
    TEST_ASSERT_EQUAL_UINT8(0x01, _node3_receive_buffer[buffer_offset]);
    TEST_ASSERT_EQUAL_UINT8(0x23, _node3_receive_buffer[buffer_offset + 1]);
    TEST_ASSERT_EQUAL_UINT8(0x45, _node3_receive_buffer[buffer_offset + 2]);
    TEST_ASSERT_EQUAL_UINT8(0x67, _node3_receive_buffer[buffer_offset + 3]);
    TEST_ASSERT_EQUAL_UINT8(0x89, _node3_receive_buffer[buffer_offset + 4]);
    TEST_ASSERT_EQUAL_UINT8(0xAB, _node3_receive_buffer[buffer_offset + 5]);
    TEST_ASSERT_EQUAL_UINT8(0xCD, _node3_receive_buffer[buffer_offset + 6]);
    TEST_ASSERT_EQUAL_UINT8(0xEF, _node3_receive_buffer[buffer_offset + 7]);
    TEST_ASSERT_EQUAL_UINT32(buffer_offset, _node3_context.bwacp_context.receive_address);

    printf("!!!!!!!!!!!! test_send_eight_bytes PASSED !!!!!!!!!!!\n");
}

/**
 * @brief Same as test_send_one_byte, but sends 254 bytes.
 *
 */
void test_send_254_bytes(void)
{
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");
    printf("!!!!!!!!!!!! Starting test_send_254_bytes !!!!!!!!!!\n");
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");

    artie_can_error_t err;

    // Create a 254-byte payload with incrementing pattern
    uint8_t send_data[254];
    for (size_t i = 0; i < sizeof(send_data); i++)
    {
        send_data[i] = (uint8_t)i;
    }
    // Address specifies the offset within the receive buffer where data should be written
    uint32_t buffer_offset = 0x4000;

    // Send from node 1 to multicast address targeting SENSOR class (nodes 2 and 3 are sensors)
    err = artie_can_bwacp_send(&_node1, send_data, sizeof(send_data), buffer_offset, ARTIE_CAN_BWACP_MULTICAST_ADDRESS, ARTIE_CAN_BWACP_CLASS_SENSOR, ARTIE_CAN_FRAME_PRIORITY_BWACP_MEDIUM);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    // Run event loops and wait for node 1 to finish sending
    // Node 1 should transition to WAITING_COMPLETE, then back to IDLE after timeout
    bool node1_complete = false;
    uint64_t start_time = get_current_time_ms();
    while (!node1_complete && (get_current_time_ms() - start_time) < DEFAULT_TIMEOUT_MS)
    {
        _run_event_loops();
        SLEEP_MS(1);
        if (artie_can_bwacp_is_busy(&_node1) == false)
        {
            node1_complete = true;
        }
    }
    TEST_ASSERT_TRUE_MESSAGE(node1_complete, "Node 1 did not complete sending");

    // Check that node 2 received the bytes at the correct buffer offset
    for (size_t i = 0; i < sizeof(send_data); i++)
    {
        TEST_ASSERT_EQUAL_UINT8((uint8_t)i, _node2_receive_buffer[buffer_offset + i]);
    }
    TEST_ASSERT_EQUAL_UINT32(buffer_offset, _node2_context.bwacp_context.receive_address);

    // Check that node 3 received the bytes at the correct buffer offset
    for (size_t i = 0; i < sizeof(send_data); i++)
    {
        TEST_ASSERT_EQUAL_UINT8((uint8_t)i, _node3_receive_buffer[buffer_offset + i]);
    }
    TEST_ASSERT_EQUAL_UINT32(buffer_offset, _node3_context.bwacp_context.receive_address);

    printf("!!!!!!!!!!!! test_send_254_bytes PASSED !!!!!!!!!!!\n");
}

/**
 * @brief Same as test_send_one_byte, but sends 255 bytes.
 *
 */
void test_send_255_bytes(void)
{
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");
    printf("!!!!!!!!!!!! Starting test_send_255_bytes !!!!!!!!!\n");
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");

    artie_can_error_t err;

    // Create a 255-byte payload with incrementing pattern
    uint8_t send_data[255];
    for (size_t i = 0; i < sizeof(send_data); i++)
    {
        send_data[i] = (uint8_t)i;
    }
    // Address specifies the offset within the receive buffer where data should be written
    uint32_t buffer_offset = 0x5000;

    // Send from node 1 to multicast address targeting SENSOR class (nodes 2 and 3 are sensors)
    err = artie_can_bwacp_send(&_node1, send_data, sizeof(send_data), buffer_offset, ARTIE_CAN_BWACP_MULTICAST_ADDRESS, ARTIE_CAN_BWACP_CLASS_SENSOR, ARTIE_CAN_FRAME_PRIORITY_BWACP_MEDIUM);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    // Run event loops and wait for node 1 to finish sending
    // Node 1 should transition to WAITING_COMPLETE, then back to IDLE after timeout
    bool node1_complete = false;
    uint64_t start_time = get_current_time_ms();
    while (!node1_complete && (get_current_time_ms() - start_time) < DEFAULT_TIMEOUT_MS)
    {
        _run_event_loops();
        SLEEP_MS(1);
        if (artie_can_bwacp_is_busy(&_node1) == false)
        {
            node1_complete = true;
        }
    }
    TEST_ASSERT_TRUE_MESSAGE(node1_complete, "Node 1 did not complete sending");

    // Check that node 2 received the bytes at the correct buffer offset
    for (size_t i = 0; i < sizeof(send_data); i++)
    {
        TEST_ASSERT_EQUAL_UINT8((uint8_t)i, _node2_receive_buffer[buffer_offset + i]);
    }
    TEST_ASSERT_EQUAL_UINT32(buffer_offset, _node2_context.bwacp_context.receive_address);

    // Check that node 3 received the bytes at the correct buffer offset
    for (size_t i = 0; i < sizeof(send_data); i++)
    {
        TEST_ASSERT_EQUAL_UINT8((uint8_t)i, _node3_receive_buffer[buffer_offset + i]);
    }
    TEST_ASSERT_EQUAL_UINT32(buffer_offset, _node3_context.bwacp_context.receive_address);

    printf("!!!!!!!!!!!! test_send_255_bytes PASSED !!!!!!!!!!!!\n");
}

/**
 * @brief Same as test_send_one_byte, but sends 256 bytes.
 *
 */
void test_send_256_bytes(void)
{
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");
    printf("!!!!!!!!!!!! Starting test_send_256_bytes !!!!!!!!!\n");
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");

    artie_can_error_t err;

    // Create a 256-byte payload with incrementing pattern
    uint8_t send_data[256];
    for (size_t i = 0; i < sizeof(send_data); i++)
    {
        send_data[i] = (uint8_t)i;
    }
    // Address specifies the offset within the receive buffer where data should be written
    uint32_t buffer_offset = 0x6000;

    // Send from node 1 to multicast address targeting SENSOR class (nodes 2 and 3 are sensors)
    err = artie_can_bwacp_send(&_node1, send_data, sizeof(send_data), buffer_offset, ARTIE_CAN_BWACP_MULTICAST_ADDRESS, ARTIE_CAN_BWACP_CLASS_SENSOR, ARTIE_CAN_FRAME_PRIORITY_BWACP_MEDIUM);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    // Run event loops and wait for node 1 to finish sending
    // Node 1 should transition to WAITING_COMPLETE, then back to IDLE after timeout
    bool node1_complete = false;
    uint64_t start_time = get_current_time_ms();
    while (!node1_complete && (get_current_time_ms() - start_time) < DEFAULT_TIMEOUT_MS)
    {
        _run_event_loops();
        SLEEP_MS(1);
        if (artie_can_bwacp_is_busy(&_node1) == false)
        {
            node1_complete = true;
        }
    }
    TEST_ASSERT_TRUE_MESSAGE(node1_complete, "Node 1 did not complete sending");

    // Check that node 2 received the bytes at the correct buffer offset
    for (size_t i = 0; i < sizeof(send_data); i++)
    {
        TEST_ASSERT_EQUAL_UINT8((uint8_t)i, _node2_receive_buffer[buffer_offset + i]);
    }
    TEST_ASSERT_EQUAL_UINT32(buffer_offset, _node2_context.bwacp_context.receive_address);

    // Check that node 3 received the bytes at the correct buffer offset
    for (size_t i = 0; i < sizeof(send_data); i++)
    {
        TEST_ASSERT_EQUAL_UINT8((uint8_t)i, _node3_receive_buffer[buffer_offset + i]);
    }
    TEST_ASSERT_EQUAL_UINT32(buffer_offset, _node3_context.bwacp_context.receive_address);

    printf("!!!!!!!!!!!! test_send_256_bytes PASSED !!!!!!!!!!!!\n");
}

/**
 * @brief Same as test_send_one_byte, but sends 257 bytes.
 *
 */
void test_send_257_bytes(void)
{
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");
    printf("!!!!!!!!!!!! Starting test_send_257_bytes !!!!!!!!!\n");
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");

    artie_can_error_t err;

    // Create a 257-byte payload with incrementing pattern
    uint8_t send_data[257];
    for (size_t i = 0; i < sizeof(send_data); i++)
    {
        send_data[i] = (uint8_t)i;
    }
    // Address specifies the offset within the receive buffer where data should be written
    uint32_t buffer_offset = 0x7000;

    // Send from node 1 to multicast address targeting SENSOR class (nodes 2 and 3 are sensors)
    err = artie_can_bwacp_send(&_node1, send_data, sizeof(send_data), buffer_offset, ARTIE_CAN_BWACP_MULTICAST_ADDRESS, ARTIE_CAN_BWACP_CLASS_SENSOR, ARTIE_CAN_FRAME_PRIORITY_BWACP_MEDIUM);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    // Run event loops and wait for node 1 to finish sending
    // Node 1 should transition to WAITING_COMPLETE, then back to IDLE after timeout
    bool node1_complete = false;
    uint64_t start_time = get_current_time_ms();
    while (!node1_complete && (get_current_time_ms() - start_time) < DEFAULT_TIMEOUT_MS)
    {
        _run_event_loops();
        SLEEP_MS(1);
        if (artie_can_bwacp_is_busy(&_node1) == false)
        {
            node1_complete = true;
        }
    }
    TEST_ASSERT_TRUE_MESSAGE(node1_complete, "Node 1 did not complete sending");

    // Check that node 2 received the bytes at the correct buffer offset
    for (size_t i = 0; i < sizeof(send_data); i++)
    {
        TEST_ASSERT_EQUAL_UINT8((uint8_t)i, _node2_receive_buffer[buffer_offset + i]);
    }
    TEST_ASSERT_EQUAL_UINT32(buffer_offset, _node2_context.bwacp_context.receive_address);

    // Check that node 3 received the bytes at the correct buffer offset
    for (size_t i = 0; i < sizeof(send_data); i++)
    {
        TEST_ASSERT_EQUAL_UINT8((uint8_t)i, _node3_receive_buffer[buffer_offset + i]);
    }
    TEST_ASSERT_EQUAL_UINT32(buffer_offset, _node3_context.bwacp_context.receive_address);

    printf("!!!!!!!!!!!! test_send_257_bytes PASSED !!!!!!!!!!!!\n");
}

/**
 * @brief Same as test_send_one_byte, but sends 46kB.
 *
 */
void test_send_46k_bytes(void)
{
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");
    printf("!!!!!!!!!!!! Starting test_send_46k_bytes !!!!!!!!!\n");
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");

    artie_can_error_t err;

    // Create a 46kB payload with incrementing pattern
    const size_t data_size = 46 * 1024; // 46kB
    uint8_t *send_data = (uint8_t *)malloc(data_size);
    TEST_ASSERT_NOT_NULL_MESSAGE(send_data, "Failed to allocate memory for send_data");

    for (size_t i = 0; i < data_size; i++)
    {
        send_data[i] = (uint8_t)(i % 256);
    }
    // Address specifies the offset within the receive buffer where data should be written
    uint32_t buffer_offset = 0x0000;

    // Send from node 1 to multicast address targeting SENSOR class (nodes 2 and 3 are sensors)
    err = artie_can_bwacp_send(&_node1, send_data, (uint32_t)data_size, buffer_offset, ARTIE_CAN_BWACP_MULTICAST_ADDRESS, ARTIE_CAN_BWACP_CLASS_SENSOR, ARTIE_CAN_FRAME_PRIORITY_BWACP_MEDIUM);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    // Run event loops and wait for node 1 to finish sending
    // Node 1 should transition to WAITING_COMPLETE, then back to IDLE after timeout
    bool node1_complete = false;
    uint64_t start_time = get_current_time_ms();
    const uint64_t timeout_minutes = 6 * 60 * 1000; // X minutes in milliseconds (in my experience, it is on the order of a few minutes ~ 3)
    while (!node1_complete && (get_current_time_ms() - start_time) < timeout_minutes)
    {
        _run_event_loops();
        SLEEP_MS(1);
        if (artie_can_bwacp_is_busy(&_node1) == false)
        {
            node1_complete = true;
        }
    }
    TEST_ASSERT_TRUE_MESSAGE(node1_complete, "Node 1 did not complete sending");

    // Check that node 2 received the bytes at the correct buffer offset
    for (size_t i = 0; i < data_size; i++)
    {
        TEST_ASSERT_EQUAL_UINT8((uint8_t)(i % 256), _node2_receive_buffer[buffer_offset + i]);
    }
    TEST_ASSERT_EQUAL_UINT32(buffer_offset, _node2_context.bwacp_context.receive_address);

    // Check that node 3 received the bytes at the correct buffer offset
    for (size_t i = 0; i < data_size; i++)
    {
        TEST_ASSERT_EQUAL_UINT8((uint8_t)(i % 256), _node3_receive_buffer[buffer_offset + i]);
    }
    TEST_ASSERT_EQUAL_UINT32(buffer_offset, _node3_context.bwacp_context.receive_address);

    // Clean up
    free(send_data);

    printf("!!!!!!!!!!!! test_send_46k_bytes PASSED !!!!!!!!!!!!\n");
}

/**
 * @brief Test to ensure we ask for a repeat when the data is invalid.
 *
 */
void test_crc_mismatch(void)
{
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");
    printf("!!!!!!!!!!!! Starting test_crc_mismatch !!!!!!!!!!!!\n");
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");

    artie_can_error_t err;

    // Create a large-ish payload to ensure we have time to corrupt data mid-transfer
    uint8_t send_data[1024];
    for (size_t i = 0; i < sizeof(send_data); i++)
    {
        send_data[i] = (uint8_t)(i & 0xFF);
    }
    uint32_t buffer_offset = 0x1000;

    // Send from node 1 to node 2 (unicast to a single node)
    err = artie_can_bwacp_send(&_node1, send_data, sizeof(send_data), buffer_offset,
                               0x02, // target node 2 specifically
                               0,    // class ignored for unicast
                               ARTIE_CAN_FRAME_PRIORITY_BWACP_MEDIUM);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    const uint64_t timeout_ms = 10000;

    // Run event loops until node 2 is actively receiving and has written some data
    bool data_received = false;
    uint64_t start_time = get_current_time_ms();
    while (!data_received && (get_current_time_ms() - start_time) < timeout_ms)
    {
        _run_event_loops();
        SLEEP_MS(1);
        if ((_node2_context.bwacp_context.state == BWACP_STATE_RECEIVING) && (_node2_context.bwacp_context.receive_bytes_written > 50))
        {
            data_received = true;
        }
    }
    TEST_ASSERT_TRUE_MESSAGE(data_received, "Node 2 did not start receiving data");

    printf("Node 2 has received %u bytes, corrupting data...\n", _node2_context.bwacp_context.receive_bytes_written);

    // Corrupt a byte that's already been written (flip all bits)
    _node2_receive_buffer[buffer_offset + 10] ^= 0xFF;

    // Let the transfer complete - it should fail CRC check and request a retransmission.
    // The transfer won't be entirely complete until the retransmission finishes
    bool done = false;
    start_time = get_current_time_ms();
    while (!done && (get_current_time_ms() - start_time) < timeout_ms)
    {
        _run_event_loops();
        SLEEP_MS(1);
        if ((artie_can_bwacp_is_busy(&_node1) == false) && (artie_can_bwacp_is_busy(&_node2) == false))
        {
            done = true;
        }
    }
    TEST_ASSERT_TRUE_MESSAGE(done, "Transfer attempt (including retransmission) did not complete");

    printf("Retransmission complete, verifying data...\n");

    // Verify that the data is now correct (retransmission overwrote the corrupted byte)
    for (size_t i = 0; i < sizeof(send_data); i++)
    {
        TEST_ASSERT_EQUAL_UINT8_MESSAGE((uint8_t)(i & 0xFF), _node2_receive_buffer[buffer_offset + i], "Data mismatch");
    }

    printf("!!!!!!!!!!!! test_crc_mismatch PASSED !!!!!!!!!!!!!\n");
}

/**
 * @brief Test addressing a single target node.
 *
 */
void test_one_target_node(void)
{
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");
    printf("!!!!!!!!!!!! Starting test_one_target_node !!!!!!!!\n");
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");

    artie_can_error_t err;

    // Create a payload
    uint8_t send_data[] = {0xAA, 0xBB, 0xCC, 0xDD};
    uint32_t buffer_offset = 0x2000;

    // Send from node 1 to node 2 specifically (unicast, not multicast)
    // Even though node 3 is the same class as node 2, it should NOT receive this
    err = artie_can_bwacp_send(&_node1, send_data, sizeof(send_data), buffer_offset,
                               0x02, // target node 2 by address
                               0,    // class ignored for unicast
                               ARTIE_CAN_FRAME_PRIORITY_BWACP_MEDIUM);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    // Run event loops and wait for node 1 to finish sending
    bool node1_complete = false;
    uint64_t start_time = get_current_time_ms();
    while (!node1_complete && (get_current_time_ms() - start_time) < DEFAULT_TIMEOUT_MS)
    {
        _run_event_loops();
        SLEEP_MS(1);
        if (_node1_context.bwacp_context.state == BWACP_STATE_IDLE)
        {
            node1_complete = true;
        }
    }
    TEST_ASSERT_TRUE_MESSAGE(node1_complete, "Node 1 did not complete sending");

    // Check that node 2 received the data at the correct buffer offset
    TEST_ASSERT_EQUAL_UINT8(0xAA, _node2_receive_buffer[buffer_offset]);
    TEST_ASSERT_EQUAL_UINT8(0xBB, _node2_receive_buffer[buffer_offset + 1]);
    TEST_ASSERT_EQUAL_UINT8(0xCC, _node2_receive_buffer[buffer_offset + 2]);
    TEST_ASSERT_EQUAL_UINT8(0xDD, _node2_receive_buffer[buffer_offset + 3]);
    TEST_ASSERT_EQUAL_UINT32(buffer_offset, _node2_context.bwacp_context.receive_address);

    // Check that node 3 did NOT receive the data (should still be all zeros)
    TEST_ASSERT_EQUAL_UINT8(0x00, _node3_receive_buffer[buffer_offset]);
    TEST_ASSERT_EQUAL_UINT8(0x00, _node3_receive_buffer[buffer_offset + 1]);
    TEST_ASSERT_EQUAL_UINT8(0x00, _node3_receive_buffer[buffer_offset + 2]);
    TEST_ASSERT_EQUAL_UINT8(0x00, _node3_receive_buffer[buffer_offset + 3]);
    // Node 3's receive_address should not be set to our buffer_offset
    TEST_ASSERT_NOT_EQUAL(buffer_offset, _node3_context.bwacp_context.receive_address);

    printf("!!!!!!!!!!!! test_one_target_node PASSED !!!!!!!!!\n");
}

/**
 * @brief Test addressing a class of nodes.
 *
 */
void test_class_of_target_nodes(void)
{
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");
    printf("!!!!!!!! Starting test_class_of_target_nodes !!!!!!\n");
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");

    artie_can_error_t err;

    // Reconfigure node 3 to be a MOTOR node instead of SENSOR
    err = artie_can_close(&_node3);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);
    memset(&_node3, 0, sizeof(_node3));
    memset(&_node3_context, 0, sizeof(_node3_context));
    memset(&_node3_udp_mcast_context, 0, sizeof(_node3_udp_mcast_context));

    err = artie_can_init_context_udp_mcast(&_node3_context, &_node3_udp_mcast_context, multicast_group, multicast_port);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    err = artie_can_init_context_bwacp(&_node3_context, 0x03, ARTIE_CAN_BWACP_CLASS_MOTOR);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    err = artie_can_bwacp_set_receive_buffer(&_node3_context, _node3_receive_buffer, sizeof(_node3_receive_buffer));
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    err = artie_can_init(&_node3_context, &_node3, ARTIE_CAN_BACKEND_UDP_MCAST, _receive_callback_node3, get_current_time_ms);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    // Create a payload
    uint8_t send_data[] = {0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88};
    uint32_t buffer_offset = 0x3000;

    // Send from node 1 to SENSOR class via multicast
    // Node 2 is SENSOR, so it should receive
    // Node 3 is MOTOR, so it should NOT receive
    err = artie_can_bwacp_send(&_node1, send_data, sizeof(send_data), buffer_offset,
                               ARTIE_CAN_BWACP_MULTICAST_ADDRESS, // multicast
                               ARTIE_CAN_BWACP_CLASS_SENSOR,      // target SENSOR class only
                               ARTIE_CAN_FRAME_PRIORITY_BWACP_MEDIUM);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    // Run event loops and wait for node 1 to finish sending
    bool node1_complete = false;
    uint64_t start_time = get_current_time_ms();
    while (!node1_complete && (get_current_time_ms() - start_time) < DEFAULT_TIMEOUT_MS)
    {
        _run_event_loops();
        SLEEP_MS(1);
        if (_node1_context.bwacp_context.state == BWACP_STATE_IDLE)
        {
            node1_complete = true;
        }
    }
    TEST_ASSERT_TRUE_MESSAGE(node1_complete, "Node 1 did not complete sending");

    // Check that node 2 (SENSOR) received the data at the correct buffer offset
    TEST_ASSERT_EQUAL_UINT8(0x11, _node2_receive_buffer[buffer_offset]);
    TEST_ASSERT_EQUAL_UINT8(0x22, _node2_receive_buffer[buffer_offset + 1]);
    TEST_ASSERT_EQUAL_UINT8(0x33, _node2_receive_buffer[buffer_offset + 2]);
    TEST_ASSERT_EQUAL_UINT8(0x44, _node2_receive_buffer[buffer_offset + 3]);
    TEST_ASSERT_EQUAL_UINT8(0x55, _node2_receive_buffer[buffer_offset + 4]);
    TEST_ASSERT_EQUAL_UINT8(0x66, _node2_receive_buffer[buffer_offset + 5]);
    TEST_ASSERT_EQUAL_UINT8(0x77, _node2_receive_buffer[buffer_offset + 6]);
    TEST_ASSERT_EQUAL_UINT8(0x88, _node2_receive_buffer[buffer_offset + 7]);
    TEST_ASSERT_EQUAL_UINT32(buffer_offset, _node2_context.bwacp_context.receive_address);

    // Check that node 3 (MOTOR) did NOT receive the data (should still be all zeros)
    TEST_ASSERT_EQUAL_UINT8(0x00, _node3_receive_buffer[buffer_offset]);
    TEST_ASSERT_EQUAL_UINT8(0x00, _node3_receive_buffer[buffer_offset + 1]);
    TEST_ASSERT_EQUAL_UINT8(0x00, _node3_receive_buffer[buffer_offset + 2]);
    TEST_ASSERT_EQUAL_UINT8(0x00, _node3_receive_buffer[buffer_offset + 3]);
    TEST_ASSERT_EQUAL_UINT8(0x00, _node3_receive_buffer[buffer_offset + 4]);
    TEST_ASSERT_EQUAL_UINT8(0x00, _node3_receive_buffer[buffer_offset + 5]);
    TEST_ASSERT_EQUAL_UINT8(0x00, _node3_receive_buffer[buffer_offset + 6]);
    TEST_ASSERT_EQUAL_UINT8(0x00, _node3_receive_buffer[buffer_offset + 7]);
    // Node 3's receive_address should not be set to our buffer_offset
    TEST_ASSERT_NOT_EQUAL(buffer_offset, _node3_context.bwacp_context.receive_address);

    printf("!!!!!!!! test_class_of_target_nodes PASSED !!!!!!!!\n");
}

/**
 * @brief Test RTACP can happen at the same time as a bulk write.
 *
 */
void test_rtacp_while_bwacp(void)
{
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");
    printf("!!!!!!!! Starting test_rtacp_while_bwacp !!!!!!!!!!\n");
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");

    artie_can_error_t err;

    // Create a large BWACP payload (1024 bytes) to ensure transfer takes some time
    uint8_t send_data[1024];
    for (size_t i = 0; i < sizeof(send_data); i++)
    {
        send_data[i] = (uint8_t)(i & 0xFF);
    }
    uint32_t buffer_offset = 0x5000;

    // Start BWACP transfer from node 1 to node 2
    err = artie_can_bwacp_send(&_node1, send_data, sizeof(send_data), buffer_offset,
                               0x02, // target node 2
                               0,    // class ignored for unicast
                               ARTIE_CAN_FRAME_PRIORITY_BWACP_MEDIUM);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    const uint64_t timeout_ms = 10000;

    // Run event loops until node 2 is actively receiving and has written some data
    bool data_received = false;
    uint64_t start_time = get_current_time_ms();
    while (!data_received && (get_current_time_ms() - start_time) < timeout_ms)
    {
        _run_event_loops();
        SLEEP_MS(1);
        if ((_node2_context.bwacp_context.state == BWACP_STATE_RECEIVING) && (_node2_context.bwacp_context.receive_bytes_written > 50))
        {
            data_received = true;
        }
    }
    TEST_ASSERT_TRUE_MESSAGE(data_received, "Node 2 did not start receiving data");

    printf("BWACP transfer in progress, sending RTACP message...\n");

    // Now send an RTACP message from node 3 to node 2 (which is busy receiving BWACP)
    artie_can_frame_rtacp_t rtacp_frame = {
        .ack = false,
        .priority = ARTIE_CAN_FRAME_PRIORITY_RTACP_HIGH,
        .source_address = 0x03,
        .target_address = 0x02,
        .nbytes = 4,
        .data = {0xAA, 0xBB, 0xCC, 0xDD, 0, 0, 0, 0}
    };
    artie_can_frame_t rtacp_can_frame;
    err = artie_can_rtacp_init_frame(&rtacp_can_frame, &rtacp_frame);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    err = artie_can_rtacp_send(&_node3, &rtacp_can_frame);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    // Continue running event loops until both transfers complete
    bool both_complete = false;
    start_time = get_current_time_ms();
    while (!both_complete && (get_current_time_ms() - start_time) < timeout_ms)
    {
        _run_event_loops();
        SLEEP_MS(1);
        if (!artie_can_bwacp_is_busy(&_node1) && !artie_can_rtacp_is_busy(&_node1))
        {
            both_complete = true;
        }
    }
    TEST_ASSERT_TRUE_MESSAGE(both_complete, "Transfers did not complete");

    printf("Both transfers complete, verifying data...\n");

    // Verify BWACP data was received correctly by node 2
    for (size_t i = 0; i < sizeof(send_data); i++)
    {
        TEST_ASSERT_EQUAL_UINT8_MESSAGE((uint8_t)(i & 0xFF), _node2_receive_buffer[buffer_offset + i], "BWACP data mismatch");
    }

    // Verify RTACP message was received correctly by node 2
    TEST_ASSERT_TRUE(_rtacp_callback_called2);
    TEST_ASSERT_EQUAL_UINT8(0x03, _rtacp_frame_received_in_callback2.source_address);
    TEST_ASSERT_EQUAL_UINT8(0x02, _rtacp_frame_received_in_callback2.target_address);
    TEST_ASSERT_EQUAL_UINT8(4, _rtacp_frame_received_in_callback2.nbytes);
    TEST_ASSERT_EQUAL_UINT8(0xAA, _rtacp_frame_received_in_callback2.data[0]);
    TEST_ASSERT_EQUAL_UINT8(0xBB, _rtacp_frame_received_in_callback2.data[1]);
    TEST_ASSERT_EQUAL_UINT8(0xCC, _rtacp_frame_received_in_callback2.data[2]);
    TEST_ASSERT_EQUAL_UINT8(0xDD, _rtacp_frame_received_in_callback2.data[3]);

    printf("!!!!!!!! test_rtacp_while_bwacp PASSED !!!!!!!!!!!\n");
}

/**
 * @brief Test that two concurrent BWACP transfers do not mess
 * each other up.
 *
 */
void test_concurrent_bwacp(void)
{
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");
    printf("!!!!!!! Starting test_concurrent_bwacp !!!!!!!!!!!!!\n");
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");

    artie_can_error_t err;

    // This test uses 4 nodes:
    // Node 1 will send to Node 2 by unicast address
    // Node 3 will send to SENSOR class via multicast
    // Node 2 is a SENSOR and should receive only from Node 1 (busy, ignores Node 3)
    // Node 4 is a SENSOR and should receive only from Node 3 (not busy, receives multicast)

    // For this test, reconfigure nodes:
    // Node 1: SBC - will send to Node 2 by address (already configured as SBC)
    // Node 2: SENSOR (already configured as SENSOR)
    // Node 3: SBC (sender B) - will send to SENSOR class (after Node 1 starts transfer)
    // Node 4: SENSOR
    err = artie_can_close(&_node3);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);
    memset(&_node3, 0, sizeof(_node3));
    memset(&_node3_context, 0, sizeof(_node3_context));
    memset(&_node3_udp_mcast_context, 0, sizeof(_node3_udp_mcast_context));

    // Node 3
    err = artie_can_init_context_udp_mcast(&_node3_context, &_node3_udp_mcast_context, multicast_group, multicast_port);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    err = artie_can_init_context_bwacp(&_node3_context, 0x03, ARTIE_CAN_BWACP_CLASS_SBC);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    err = artie_can_bwacp_set_receive_buffer(&_node3_context, _node3_receive_buffer, sizeof(_node3_receive_buffer));
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    err = artie_can_init(&_node3_context, &_node3, ARTIE_CAN_BACKEND_UDP_MCAST, _receive_callback_node3, get_current_time_ms);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    // Node 4
    err = artie_can_init_context_udp_mcast(&_node4_context, &_node4_udp_mcast_context, multicast_group, multicast_port);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    err = artie_can_init_context_bwacp(&_node4_context, 0x04, ARTIE_CAN_BWACP_CLASS_SENSOR);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    err = artie_can_bwacp_set_receive_buffer(&_node4_context, _node4_receive_buffer, sizeof(_node4_receive_buffer));
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    err = artie_can_init(&_node4_context, &_node4, ARTIE_CAN_BACKEND_UDP_MCAST, _receive_callback_node4, get_current_time_ms);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    // Create two different payloads
    uint8_t send_data_A[512]; // From Node 1 to Node 2
    for (size_t i = 0; i < sizeof(send_data_A); i++)
    {
        send_data_A[i] = (uint8_t)(i & 0xFF);
    }

    uint8_t send_data_B[512]; // From Node 3 to SENSOR class (multicast)
    for (size_t i = 0; i < sizeof(send_data_B); i++)
    {
        send_data_B[i] = (uint8_t)((i + 128) & 0xFF); // Different pattern
    }

    const uint32_t timeout_ms = 50000;
    uint32_t buffer_offset_A = 0x0060;
    uint32_t buffer_offset_B = 0x0700; // enough space so that no overlap with the cross-talk we are testing for

    // Start transfer from Node 1 to Node 2 by address (unicast)
    err = artie_can_bwacp_send(&_node1, send_data_A, sizeof(send_data_A), buffer_offset_A,
                               0x02, // target Node 2 specifically by address
                               0,    // class ignored for unicast
                               ARTIE_CAN_FRAME_PRIORITY_BWACP_MEDIUM);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    // Wait a bit for Node 2 to start receiving
    uint64_t start_time = get_current_time_ms();
    bool node2_started = false;
    while (!node2_started && (get_current_time_ms() - start_time) < timeout_ms)
    {
        _run_event_loops();
        SLEEP_MS(1);
        if (artie_can_bwacp_is_busy(&_node2) && _node2_context.bwacp_context.receive_bytes_written > 0)
        {
            node2_started = true;
        }
    }
    TEST_ASSERT_TRUE_MESSAGE(node2_started, "Node 2 did not start receiving from Node 1");

    printf("Node 2 is now busy receiving from Node 1, starting Node 3's multicast...\n");

    // Now start transfer from Node 3 to SENSOR class (multicast)
    // Node 2 is SENSOR class, but it's busy receiving from Node 1, so it should ignore this
    // Node 4 is SENSOR class and not busy, so it should receive this
    err = artie_can_bwacp_send(&_node3, send_data_B, sizeof(send_data_B), buffer_offset_B,
                               ARTIE_CAN_BWACP_MULTICAST_ADDRESS, // multicast
                               ARTIE_CAN_BWACP_CLASS_SENSOR,      // target SENSOR class
                               ARTIE_CAN_FRAME_PRIORITY_BWACP_MEDIUM);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    // Run event loops until both transfers complete
    bool all_complete = false;
    start_time = get_current_time_ms();
    while (!all_complete && (get_current_time_ms() - start_time) < timeout_ms)
    {
        _run_event_loops();
        SLEEP_MS(1);
        if (!artie_can_bwacp_is_busy(&_node1) && !artie_can_bwacp_is_busy(&_node3))
        {
            all_complete = true;
        }
    }
    TEST_ASSERT_TRUE_MESSAGE(all_complete, "Transfers did not complete");

    printf("Both transfers complete, verifying data...\n");

    // Verify Node 2 received data from Node 1 correctly
    for (size_t i = 0; i < sizeof(send_data_A); i++)
    {
        TEST_ASSERT_EQUAL_UINT8_MESSAGE((uint8_t)(i & 0xFF), _node2_receive_buffer[buffer_offset_A + i], "Node 2 did not receive correct data from Node 1");
    }

    // Verify Node 2 did NOT receive data from Node 3 (B) - should still be zeros
    // Check a few bytes at buffer_offset_B
    TEST_ASSERT_EQUAL_UINT8_MESSAGE(0x00, _node2_receive_buffer[buffer_offset_B], "Node 2 should not have received multicast from Node 3 (was busy)");
    TEST_ASSERT_EQUAL_UINT8_MESSAGE(0x00, _node2_receive_buffer[buffer_offset_B + 1], "Node 2 should not have received multicast from Node 3 (was busy)");
    TEST_ASSERT_EQUAL_UINT8_MESSAGE(0x00, _node2_receive_buffer[buffer_offset_B + 100], "Node 2 should not have received multicast from Node 3 (was busy)");

    // Verify Node 4 received data from Node 3 correctly
    for (size_t i = 0; i < sizeof(send_data_B); i++)
    {
        TEST_ASSERT_EQUAL_UINT8_MESSAGE((uint8_t)((i + 128) & 0xFF), _node4_receive_buffer[buffer_offset_B + i], "Node 4 did not receive correct data from Node 3");
    }

    // Verify Node 4 did NOT receive data from Node 1 - should still be zeros
    TEST_ASSERT_EQUAL_UINT8_MESSAGE(0x00, _node4_receive_buffer[buffer_offset_A], "Node 4 should not have received from Node 1");
    TEST_ASSERT_EQUAL_UINT8_MESSAGE(0x00, _node4_receive_buffer[buffer_offset_A + 1], "Node 4 should not have received from Node 1");
    TEST_ASSERT_EQUAL_UINT8_MESSAGE(0x00, _node4_receive_buffer[buffer_offset_A + 100], "Node 4 should not have received from Node 1");

    printf("!!!!!!! test_concurrent_bwacp PASSED !!!!!!!!!!!!!!!\n");
}

/**
 * @brief Main function - runs all tests.
 *
 * This function sets up the Unity test runner and executes all tests.
 */
int main(void)
{
    multicast_group = test_multicast_group(_multicast_group_buffer, sizeof(_multicast_group_buffer), 2);
    // Printed so a CI log says which bus this run used; the group is per-process, so it is
    // the first thing worth knowing if a run ever does look like it heard someone else.
    printf("Test bus: %s:%u\n", multicast_group, (unsigned int)multicast_port);

    // Initialize Unity test framework
    UNITY_BEGIN();

    // Run tests
    RUN_TEST(test_send_one_byte);
    RUN_TEST(test_send_four_bytes);
    RUN_TEST(test_send_eight_bytes);
    RUN_TEST(test_send_254_bytes);
    RUN_TEST(test_send_255_bytes);
    RUN_TEST(test_send_256_bytes);
    RUN_TEST(test_send_257_bytes);
    RUN_TEST(test_crc_mismatch);
    RUN_TEST(test_one_target_node);
    RUN_TEST(test_class_of_target_nodes);
    RUN_TEST(test_rtacp_while_bwacp);
    RUN_TEST(test_concurrent_bwacp);
    RUN_TEST(test_send_46k_bytes);

    // Finish and return results
    return UNITY_END();
}
