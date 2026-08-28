#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef _WIN32
#include <process.h>
#include <winsock2.h>
#include <windows.h>
#else
#include <sys/time.h>
#include <time.h>
#include <unistd.h>
#endif
#include "unity.h"
#include "artie_can.h"
#include "util.h"

const char *test_multicast_group(char *out, size_t out_size, uint8_t suite_id)
{
    if ((out == NULL) || (out_size < 16U))
    {
        return NULL;
    }

    const char *override = getenv("ARTIE_CAN_TEST_MCAST_GROUP");
    if ((override != NULL) && (override[0] != '\0'))
    {
        snprintf(out, out_size, "%s", override);
        return out;
    }

    // FNV-1a over everything that distinguishes this test run from another one.
    uint32_t hash = 2166136261u;
    #define MIX_BYTES(ptr, len) do { \
        const unsigned char *_p = (const unsigned char *)(ptr); \
        for (size_t _i = 0; _i < (size_t)(len); _i++) { hash = (hash ^ _p[_i]) * 16777619u; } \
    } while (0)

    // The hostname is the load-bearing one in a container: Docker sets it to the container ID, and
    // it is the only one of these three inputs that differs between two containers. The process ID
    // does not - every container gets its own PID namespace, so the test binary is PID 1 in all of
    // them, which is exactly how an earlier version of this function ended up handing every
    // container the same group.
    char hostname[256] = {0};
    if (gethostname(hostname, (int)sizeof(hostname) - 1) == 0)
    {
        MIX_BYTES(hostname, strlen(hostname));
    }

    // Separates two processes inside one container, where the hostname is shared.
#ifdef _WIN32
    unsigned int pid = (unsigned int)_getpid();
#else
    unsigned int pid = (unsigned int)getpid();
#endif
    MIX_BYTES(&pid, sizeof(pid));

    // Separates two runs that are otherwise identical, such as the same container restarted.
#ifdef _WIN32
    LARGE_INTEGER counter;
    QueryPerformanceCounter(&counter);
    long long now = counter.QuadPart;
#else
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    long long now = ((long long)ts.tv_sec * 1000000000LL) + ts.tv_nsec;
#endif
    MIX_BYTES(&now, sizeof(now));

    #undef MIX_BYTES

    // 239.0.0.0/8 is the administratively scoped block, so anything in it is safe to make up.
    // Both middle octets are kept in 1..254: 0 and 255 are legal in a group address but are the
    // kind of thing that trips up network gear and packet captures, and avoiding them costs
    // nothing here. That leaves ~64k groups, which is ample for the handful of test runs that
    // could ever be in flight on one host at once.
    unsigned int high = ((hash >> 16) & 0xFFU) % 254U;
    unsigned int low = ((hash >> 8) & 0xFFU) % 254U;

    snprintf(out, out_size, "239.%u.%u.%u", high + 1U, low + 1U, (unsigned int)(suite_id % 254U) + 1U);
    return out;
}

void assert_frames_equal(volatile const artie_can_frame_t *frame1, volatile const artie_can_frame_t *frame2)
{
    // Member item comparison
    TEST_ASSERT_EQUAL_UINT32(frame1->id, frame2->id);
    TEST_ASSERT_EQUAL_UINT(frame1->dlc, frame2->dlc);
    TEST_ASSERT_EQUAL_UINT8_ARRAY(frame1->data, frame2->data, frame1->dlc);
}

void assert_rtacp_frames_equal(volatile const artie_can_frame_rtacp_t *frame1, volatile const artie_can_frame_rtacp_t *frame2)
{
    // Member item comparison
    TEST_ASSERT_EQUAL_UINT8(frame1->ack, frame2->ack);
    TEST_ASSERT_EQUAL_UINT8(frame1->priority, frame2->priority);
    TEST_ASSERT_EQUAL_UINT8(frame1->source_address, frame2->source_address);
    TEST_ASSERT_EQUAL_UINT8(frame1->target_address, frame2->target_address);
    TEST_ASSERT_EQUAL_UINT8(frame1->nbytes, frame2->nbytes);
    TEST_ASSERT_EQUAL_UINT8_ARRAY(frame1->data, frame2->data, frame1->nbytes);
}

uint64_t get_current_time_ms(void)
{
#if defined(_WIN32) || defined(_WIN64)
    // Windows implementation using GetSystemTimeAsFileTime
    FILETIME ft;
    GetSystemTimeAsFileTime(&ft);

    // Convert FILETIME (100-ns intervals since Jan 1, 1601) to milliseconds since Unix epoch
    uint64_t time = ((uint64_t)ft.dwHighDateTime << 32) | ft.dwLowDateTime; // Time in 100-ns intervals
    time -= 116444736000000000ULL; // Convert from Windows epoch (1601) to Unix epoch (1970)
    return time / 10000; // Convert from 100-ns intervals to milliseconds
#else
    // Here is a simple implementation using gettimeofday for POSIX systems:
    // (AI generated, untested code)
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return (int64_t)(tv.tv_sec) * 1000 + (int64_t)(tv.tv_usec) / 1000;
#endif
}

artie_can_error_t wait_with_timeout(volatile bool *condition, uint32_t timeout_ms, void (*tick_callback)(void))
{
    uint64_t start_time_ms = get_current_time_ms();
    while (!(*condition))
    {
        if ((get_current_time_ms() - start_time_ms) >= (uint64_t)timeout_ms)
        {
            return ARTIE_CAN_ERR_TIMEOUT;
        }

        // Call the tick callback if provided (for event loop processing)
        if (tick_callback != NULL)
        {
            tick_callback();
        }

        SLEEP_MS(1);  // Sleep for 1ms to allow event loops to process
    }
    return ARTIE_CAN_ERR_NONE;
}
