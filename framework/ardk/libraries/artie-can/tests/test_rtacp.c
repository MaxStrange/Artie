/**
 * @file test_rtacp.c
 * @brief Test the RTACP (Real Time Artie CAN Protocol) implementation.
 * Uses UDP Multicast backend.
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

// Default timeout for receive calls in tests (in milliseconds)
#define DEFAULT_TIMEOUT_MS 3000

// Timeout for retrying send operations when busy (in milliseconds)
#define SEND_RETRY_TIMEOUT_MS 100

// Multicast configuration for all test nodes
// Each test process gets its own multicast group, so two runs on one host - two CI jobs on
// Docker's shared default bridge, or a developer running this while a job runs - do not end
// up sharing a simulated bus. See test_multicast_group() in util.c.
static char _multicast_group_buffer[16];
static const char *multicast_group = NULL; // set in main() via test_multicast_group(), suite 1
static const uint16_t multicast_port = 5007;

static artie_can_context_t _node1_context;
static artie_can_context_t _node2_context;
static artie_can_context_t _node3_context;
static artie_can_backend_t _node1;
static artie_can_backend_t _node2;
static artie_can_backend_t _node3;
static artie_can_udp_mcast_context_t _node1_udp_mcast_context;
static artie_can_udp_mcast_context_t _node2_udp_mcast_context;
static artie_can_udp_mcast_context_t _node3_udp_mcast_context;

// A flag to indicate whether the callback has been called for tests that use the callback.
static volatile bool _callback_called1 = false;
static volatile bool _callback_called2 = false;
static volatile bool _callback_called3 = false;
static volatile artie_can_frame_rtacp_t _frame_received_in_callback1;
static volatile artie_can_frame_rtacp_t _frame_received_in_callback2;
static volatile artie_can_frame_rtacp_t _frame_received_in_callback3;

/** The callback that node1 uses to receive messages. */
static void _receive_callback_node1(const artie_can_frame_t *frame)
{
    // Parse the received frame into RTACP format and store it in the callback storage variable for node 1.
    artie_can_frame_rtacp_t rtacp_frame_received;
    artie_can_error_t err = artie_can_rtacp_parse_frame(frame, &rtacp_frame_received);
    if (err == ARTIE_CAN_ERR_NONE)
    {
        // Due to volatile qualifier, we can't use memcpy here, so we have to copy member by member.
        _frame_received_in_callback1.ack = rtacp_frame_received.ack;
        _frame_received_in_callback1.priority = rtacp_frame_received.priority;
        _frame_received_in_callback1.source_address = rtacp_frame_received.source_address;
        _frame_received_in_callback1.target_address = rtacp_frame_received.target_address;
        _frame_received_in_callback1.nbytes = rtacp_frame_received.nbytes;
        for (uint8_t i = 0; i < rtacp_frame_received.nbytes; i++)
        {
            _frame_received_in_callback1.data[i] = rtacp_frame_received.data[i];
        }
        _callback_called1 = true;
    }
}

/** The callback that node2 uses to receive messages. */
static void _receive_callback_node2(const artie_can_frame_t *frame)
{
    // Parse the received frame into RTACP format and store it in the callback storage variable for node 2.
    artie_can_frame_rtacp_t rtacp_frame_received;
    artie_can_error_t err = artie_can_rtacp_parse_frame(frame, &rtacp_frame_received);
    if (err == ARTIE_CAN_ERR_NONE)
    {
        // Due to volatile qualifier, we can't use memcpy here, so we have to copy member by member.
        _frame_received_in_callback2.ack = rtacp_frame_received.ack;
        _frame_received_in_callback2.priority = rtacp_frame_received.priority;
        _frame_received_in_callback2.source_address = rtacp_frame_received.source_address;
        _frame_received_in_callback2.target_address = rtacp_frame_received.target_address;
        _frame_received_in_callback2.nbytes = rtacp_frame_received.nbytes;
        for (uint8_t i = 0; i < rtacp_frame_received.nbytes; i++)
        {
            _frame_received_in_callback2.data[i] = rtacp_frame_received.data[i];
        }
        _callback_called2 = true;
    }
}

/** The callback that node3 uses to receive messages. */
static void _receive_callback_node3(const artie_can_frame_t *frame)
{
    // Parse the received frame into RTACP format and store it in the callback storage variable for node 3.
    artie_can_frame_rtacp_t rtacp_frame_received;
    artie_can_error_t err = artie_can_rtacp_parse_frame(frame, &rtacp_frame_received);
    if (err == ARTIE_CAN_ERR_NONE)
    {
        // Due to volatile qualifier, we can't use memcpy here, so we have to copy member by member.
        _frame_received_in_callback3.ack = rtacp_frame_received.ack;
        _frame_received_in_callback3.priority = rtacp_frame_received.priority;
        _frame_received_in_callback3.source_address = rtacp_frame_received.source_address;
        _frame_received_in_callback3.target_address = rtacp_frame_received.target_address;
        _frame_received_in_callback3.nbytes = rtacp_frame_received.nbytes;
        for (uint8_t i = 0; i < rtacp_frame_received.nbytes; i++)
        {
            _frame_received_in_callback3.data[i] = rtacp_frame_received.data[i];
        }
        _callback_called3 = true;
    }
}

static void _reset_frame(volatile artie_can_frame_rtacp_t *frame)
{
    frame->ack = false;
    frame->priority = 0;
    frame->source_address = 0;
    frame->target_address = 0;
    frame->nbytes = 0;
    for (size_t i = 0; i < ARTIE_CAN_RTACP_MAX_DATA_BYTES; i++)
    {
        frame->data[i] = 0;
    }
}

static void _run_event_loops(void)
{
    // Run one tick of the event loop for each node
    artie_can_error_t err;
    err = artie_can_tick(&_node1);
    if (err)
    {
        if (ARTIE_CAN_ERR_ONLY_RETRIABLE(err))
        {
            printf("Retriable error occurred while ticking node 1: %d\n", err);
        }
        else
        {
            printf("Non-retriable error occurred while ticking node 1: %d\n", err);
            TEST_FAIL_MESSAGE("Error ticking node 1");
        }
    }

    err = artie_can_tick(&_node2);
    if (err)
    {
        if (ARTIE_CAN_ERR_ONLY_RETRIABLE(err))
        {
            printf("Retriable error occurred while ticking node 2: %d\n", err);
        }
        else
        {
            printf("Non-retriable error occurred while ticking node 2: %d\n", err);
            TEST_FAIL_MESSAGE("Error ticking node 2");
        }
    }

    err = artie_can_tick(&_node3);
    if (err)
    {
        if (ARTIE_CAN_ERR_ONLY_RETRIABLE(err))
        {
            printf("Retriable error occurred while ticking node 3: %d\n", err);
        }
        else
        {
            printf("Non-retriable error occurred while ticking node 3: %d\n", err);
            TEST_FAIL_MESSAGE("Error ticking node 3");
        }
    }

}

/**
 * @brief Wrapper function to send an RTACP frame with retry on busy.
 * Retries sending if ARTIE_CAN_ERR_SEND_BUSY is returned, up to the timeout.
 *
 * @param handle Pointer to the backend handle.
 * @param frame Pointer to the frame to send.
 * @return artie_can_error_t Error code from the send operation.
 */
static artie_can_error_t _rtacp_send_with_retry(artie_can_backend_t *handle, const artie_can_frame_t *frame)
{
    artie_can_error_t err;
    uint64_t start_time = get_current_time_ms();

    while ((get_current_time_ms() - start_time) < SEND_RETRY_TIMEOUT_MS)
    {
        err = artie_can_rtacp_send(handle, frame);
        if (err == ARTIE_CAN_ERR_SEND_BUSY)
        {
            // Run event loops to allow the system to make progress
            _run_event_loops();
            SLEEP_MS(1);
            continue;
        }
        else
        {
            // Either success or a different error - return it
            return err;
        }
    }

    // Timeout - return the last error (which should be SEND_BUSY)
    return err;
}

/**
 * @brief Setup function called before each test.
 *
 * This function runs before each individual test in this file.
 * Use it to initialize any state needed for your tests.
 */
void setUp(void)
{
    artie_can_error_t err;

    // Reset the callback items
    _callback_called1 = false;
    _callback_called2 = false;
    _callback_called3 = false;

    // Due to volatile qualifier, we can't use memset here, so we have to reset member by member.
    _reset_frame(&_frame_received_in_callback1);
    _reset_frame(&_frame_received_in_callback2);
    _reset_frame(&_frame_received_in_callback3);

    // Set up the nodes with UDP multicast contexts
    err = artie_can_init_context_udp_mcast(&_node1_context, &_node1_udp_mcast_context, multicast_group, multicast_port);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    err = artie_can_init_context_udp_mcast(&_node2_context, &_node2_udp_mcast_context, multicast_group, multicast_port);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    err = artie_can_init_context_udp_mcast(&_node3_context, &_node3_udp_mcast_context, multicast_group, multicast_port);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    // Set up the nodes to use RTACP
    err = artie_can_init_context_rtacp(&_node1_context, 0x01); // Source address 0x01
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    err = artie_can_init_context_rtacp(&_node2_context, 0x02); // Source address 0x02
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    err = artie_can_init_context_rtacp(&_node3_context, 0x03); // Source address 0x03
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

    // Clean up contexts by zeroing them out (not strictly necessary, but good practice since we are reusing them in setUp)
    memset(&_node1, 0, sizeof(_node1));
    memset(&_node2, 0, sizeof(_node2));
    memset(&_node3, 0, sizeof(_node3));
    memset(&_node1_context, 0, sizeof(_node1_context));
    memset(&_node2_context, 0, sizeof(_node2_context));
    memset(&_node3_context, 0, sizeof(_node3_context));
    memset(&_node1_udp_mcast_context, 0, sizeof(_node1_udp_mcast_context));
    memset(&_node2_udp_mcast_context, 0, sizeof(_node2_udp_mcast_context));
    memset(&_node3_udp_mcast_context, 0, sizeof(_node3_udp_mcast_context));
}

/**
 * @brief Test that we can broadcast a message from one node and receive it on another.
 *
 */
void test_broadcast(void)
{
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");
    printf("!!!!!!!!!!!! Starting test_broadcast !!!!!!!!!!!!!!!\n");
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");

    artie_can_error_t err;

    // Create a frame to send
    uint8_t data_bytes[] = {0xDE, 0xAD, 0xBE, 0xEF};
    artie_can_frame_rtacp_t rtacp_frame = {
        .ack = false,
        .priority = ARTIE_CAN_FRAME_PRIORITY_RTACP_MEDIUM,
        .source_address = 0x01,
        .target_address = ARTIE_CAN_RTACP_TARGET_ADDRESS_BROADCAST,
        .nbytes = sizeof(data_bytes),
        .data = {0}
    };
    memcpy(rtacp_frame.data, data_bytes, sizeof(data_bytes));
    artie_can_frame_t frame_to_send;
    err = artie_can_rtacp_init_frame(&frame_to_send, &rtacp_frame);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    // Send the frame from node 1
    err = _rtacp_send_with_retry(&_node1, &frame_to_send);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);
    _run_event_loops();

    // Blocking receive on node 2 to get the frame
    err = wait_with_timeout(&_callback_called2, DEFAULT_TIMEOUT_MS, _run_event_loops);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    // Check that the received frame matches the sent frame
    assert_rtacp_frames_equal(&rtacp_frame, &_frame_received_in_callback2);

    // Blocking receive on node 3 to get the frame
    err = wait_with_timeout(&_callback_called3, DEFAULT_TIMEOUT_MS, _run_event_loops);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    // Check that the received frame matches the sent frame
    assert_rtacp_frames_equal(&rtacp_frame, &_frame_received_in_callback3);
}

/**
 * @brief Test that we can send a message from one node to another (not broadcast) and receive it.
 *
 */
void test_send_to_specific_address(void)
{
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");
    printf("!!!!!!!!!!!! Starting test_send_to_specific_address !!!!!!!!!!!!!!!\n");
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");

    artie_can_error_t err;

    // Create a frame to send from node 1 to node 2 (address 0x02)
    uint8_t data_bytes[] = {0xAA, 0xBB, 0xCC, 0xDD};
    artie_can_frame_rtacp_t rtacp_frame = {
        .ack = false,
        .priority = ARTIE_CAN_FRAME_PRIORITY_RTACP_MEDIUM,
        .source_address = 0x01,
        .target_address = 0x02,
        .nbytes = sizeof(data_bytes),
        .data = {0}
    };
    memcpy(rtacp_frame.data, data_bytes, sizeof(data_bytes));

    // Create the raw frame that we will send from the RTACP frame
    artie_can_frame_t frame_to_send;
    err = artie_can_rtacp_init_frame(&frame_to_send, &rtacp_frame);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    // Send the frame from node 1
    err = _rtacp_send_with_retry(&_node1, &frame_to_send);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    // Blocking receive on node 2 to get the frame
    err = wait_with_timeout(&_callback_called2, DEFAULT_TIMEOUT_MS, _run_event_loops);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    // Check that the received frame matches the sent frame
    assert_rtacp_frames_equal(&rtacp_frame, &_frame_received_in_callback2);
}


/**
 * @brief Test that if we send a message to a specific target address,
 * only the node with that address receives it and not other nodes.
 *
 */
void test_send_to_specific_address_only_received_by_target(void)
{
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");
    printf("!!!!!!!!!!!! Starting test_send_to_specific_address_only_received_by_target !!!!!!!\n");
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");

    artie_can_error_t err;

    // Create a frame to send from node 1 to node 2 (address 0x02)
    uint8_t data_bytes[] = {0x11, 0x22, 0x33, 0x44};
    artie_can_frame_rtacp_t rtacp_frame = {
        .ack = false,
        .priority = ARTIE_CAN_FRAME_PRIORITY_RTACP_MEDIUM,
        .source_address = 0x01,
        .target_address = 0x02, // Node 2's address
        .nbytes = sizeof(data_bytes),
        .data = {0}
    };
    memcpy(rtacp_frame.data, data_bytes, sizeof(data_bytes));
    artie_can_frame_t frame_to_send;
    err = artie_can_rtacp_init_frame(&frame_to_send, &rtacp_frame);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    // Send the frame from node 1
    err = _rtacp_send_with_retry(&_node1, &frame_to_send);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);
    _run_event_loops();

    // Blocking receive on node 2 to get the frame
    err = wait_with_timeout(&_callback_called2, DEFAULT_TIMEOUT_MS, _run_event_loops);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    // Check that the received frame matches the sent frame
    assert_rtacp_frames_equal(&rtacp_frame, &_frame_received_in_callback2);

    // Ensure node 3 did NOT receive the frame.
    // We wait a short amount of time to be sure.
    SLEEP_MS(100);
    TEST_ASSERT_FALSE(_callback_called3);
}


/**
 * @brief Test sending multiple messages in a row. Receipt of all messages is required,
 * but order is not guaranteed according to RTACP.
 *
 */
void test_send_multiple_messages(void)
{
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");
    printf("!!!!!!!!!!!! Starting test_send_multiple_messages !!!!!!!\n");
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");

    artie_can_error_t err;
    artie_can_frame_rtacp_t sent_frames[5];
    const int num_messages = ARRAY_LENGTH(sent_frames);

    for (int i = 0; i < num_messages; i++)
    {
        // Reset node 2 callback flag for each message
        _callback_called2 = false;
        _reset_frame(&_frame_received_in_callback2);

        uint8_t data_bytes[] = {(uint8_t)i, (uint8_t)(i + 1), (uint8_t)(i + 2), (uint8_t)(i + 3)};
        artie_can_frame_rtacp_t rtacp_frame = {
            .ack = false,
            .priority = ARTIE_CAN_FRAME_PRIORITY_RTACP_MEDIUM,
            .source_address = 0x01,
            .target_address = 0x02,
            .nbytes = ARRAY_LENGTH(data_bytes),
            .data = {0}
        };
        memcpy(rtacp_frame.data, data_bytes, sizeof(data_bytes));

        // Create the frame
        artie_can_frame_t frame_to_send;
        err = artie_can_rtacp_init_frame(&frame_to_send, &rtacp_frame);
        TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

        // Send the frame with retry on busy
        err = _rtacp_send_with_retry(&_node1, &frame_to_send);
        TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);
        _run_event_loops();

        // Ensure node 2 receives the frame
        err = wait_with_timeout(&_callback_called2, DEFAULT_TIMEOUT_MS, _run_event_loops);
        TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

        // Ensure the received frame matches the sent frame
        assert_rtacp_frames_equal(&rtacp_frame, &_frame_received_in_callback2);
    }
}

/**
 * @brief Test sending a message to a node and then having that node echo back the message.
 * This tests both sending and receiving in the same node.
 *
 */
void test_echo_message(void)
{
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");
    printf("!!!!!!!!!!!! Starting test_echo_message !!!!!!!!!!!!!!!\n");
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");

    artie_can_error_t err;

    // Node 1 sends to Node 2
    uint8_t data_bytes[] = {0x1, 0x2, 0x3, 0x4, 0x5, 0x6, 0x7, 0x8};
    artie_can_frame_rtacp_t frame1to2 = {
        .ack = false,
        .priority = ARTIE_CAN_FRAME_PRIORITY_RTACP_HIGH,
        .source_address = 0x01,
        .target_address = 0x02,
        .nbytes = sizeof(data_bytes),
        .data = {0}
    };
    memcpy(frame1to2.data, data_bytes, sizeof(data_bytes));

    // Initialize the raw frame
    artie_can_frame_t can_frame1to2;
    err = artie_can_rtacp_init_frame(&can_frame1to2, &frame1to2);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    // Send from 1 to 2
    err = _rtacp_send_with_retry(&_node1, &can_frame1to2);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);
    _run_event_loops();

    // Wait for Node 2 to receive
    err = wait_with_timeout(&_callback_called2, DEFAULT_TIMEOUT_MS, _run_event_loops);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);
    assert_rtacp_frames_equal(&frame1to2, &_frame_received_in_callback2);

    // Node 2 echoes back to Node 1
    artie_can_frame_rtacp_t frame2to1 = {
        .ack = false,
        .priority = ARTIE_CAN_FRAME_PRIORITY_RTACP_HIGH,
        .source_address = 0x02,
        .target_address = 0x01,
        .nbytes = _frame_received_in_callback2.nbytes,
        .data = {0}
    };

    // Can't memcpy because of the volatile
    for (uint8_t i = 0; i < frame2to1.nbytes; i++) {
        frame2to1.data[i] = _frame_received_in_callback2.data[i];
    }

    // Initialize the raw frame
    artie_can_frame_t can_frame2to1;
    err = artie_can_rtacp_init_frame(&can_frame2to1, &frame2to1);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

    // Send from 2 to 1
    err = _rtacp_send_with_retry(&_node2, &can_frame2to1);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);
    _run_event_loops();

    // Wait for Node 1 to receive echo
    err = wait_with_timeout(&_callback_called1, DEFAULT_TIMEOUT_MS, _run_event_loops);
    TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);
    assert_rtacp_frames_equal(&frame2to1, &_frame_received_in_callback1);
}

/**
 * @brief Test sending a whole bunch of messages in a row and echoing them all back, to test the robustness of the system under load.
 *
 */
void test_send_lots_of_messages(void)
{
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");
    printf("!!!!!!!!!!!! Starting test_send_lots_of_messages !!!!!!!!!!!!!!!\n");
    printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");

    artie_can_error_t err;
    const int num_messages = 100;

    for (int i = 0; i < num_messages; i++)
    {
        printf("----- Sending message %d/%d -----\n", i + 1, num_messages);

        // Reset callback flags
        _callback_called1 = false;
        _callback_called2 = false;
        _reset_frame(&_frame_received_in_callback1);
        _reset_frame(&_frame_received_in_callback2);

        // Node 1 sends to Node 2
        uint8_t data_bytes[ARTIE_CAN_RTACP_MAX_DATA_BYTES];
        for (int j = 0; j < ARTIE_CAN_RTACP_MAX_DATA_BYTES; j++)
        {
            data_bytes[j] = (uint8_t)(i + j);
        }

        artie_can_frame_rtacp_t frame1to2 = {
            .ack = false,
            .priority = ARTIE_CAN_FRAME_PRIORITY_RTACP_MEDIUM,
            .source_address = 0x01,
            .target_address = 0x02,
            .nbytes = sizeof(data_bytes),
            .data = {0}
        };
        memcpy(frame1to2.data, data_bytes, sizeof(data_bytes));

        artie_can_frame_t can_frame1to2;
        err = artie_can_rtacp_init_frame(&can_frame1to2, &frame1to2);
        TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

        err = _rtacp_send_with_retry(&_node1, &can_frame1to2);
        TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);
        _run_event_loops();

        // Wait for Node 2 to receive
        err = wait_with_timeout(&_callback_called2, DEFAULT_TIMEOUT_MS, _run_event_loops);
        TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);
        assert_rtacp_frames_equal(&frame1to2, &_frame_received_in_callback2);

        // Node 2 echoes back to Node 1
        artie_can_frame_rtacp_t frame2to1 = {
            .ack = false,
            .priority = ARTIE_CAN_FRAME_PRIORITY_RTACP_MEDIUM,
            .source_address = 0x02,
            .target_address = 0x01,
            .nbytes = _frame_received_in_callback2.nbytes,
            .data = {0}
        };

        // Can't memcpy because of the volatile
        for (uint8_t k = 0; k < frame2to1.nbytes; k++) {
            frame2to1.data[k] = _frame_received_in_callback2.data[k];
        }

        artie_can_frame_t can_frame2to1;
        err = artie_can_rtacp_init_frame(&can_frame2to1, &frame2to1);
        TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);

        err = _rtacp_send_with_retry(&_node2, &can_frame2to1);
        TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);
        _run_event_loops();

        // Wait for Node 1 to receive echo
        err = wait_with_timeout(&_callback_called1, DEFAULT_TIMEOUT_MS, _run_event_loops);
        TEST_ASSERT_EQUAL_INT(ARTIE_CAN_ERR_NONE, err);
        assert_rtacp_frames_equal(&frame2to1, &_frame_received_in_callback1);
    }
}

/**
 * @brief Main function - runs all tests.
 *
 * This function sets up the Unity test runner and executes all tests.
 */
int main(void)
{
    multicast_group = test_multicast_group(_multicast_group_buffer, sizeof(_multicast_group_buffer), 1);
    // Printed so a CI log says which bus this run used; the group is per-process, so it is
    // the first thing worth knowing if a run ever does look like it heard someone else.
    printf("Test bus: %s:%u\n", multicast_group, (unsigned int)multicast_port);

    // Initialize Unity test framework
    UNITY_BEGIN();

    // Run tests
    RUN_TEST(test_broadcast);
    RUN_TEST(test_send_to_specific_address);
    RUN_TEST(test_send_to_specific_address_only_received_by_target);
    RUN_TEST(test_send_multiple_messages);
    RUN_TEST(test_echo_message);
    RUN_TEST(test_send_lots_of_messages);

    // Finish and return results
    return UNITY_END();
}
