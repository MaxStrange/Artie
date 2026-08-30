/**
 * @file errors.h
 * @brief Error byte and associated enum.
 *
 */
#pragma once

#ifdef __cplusplus
extern "C" {
#endif

/** Allowed errors. */
typedef enum {
    EPERM   = 0x0001,      // Operation not permitted
    ENOENT  = 0x0002,      // No such resource
    EINTR   = 0x0004,      // Interrupted
    EIO     = 0x0005,      // I/O Error
    ENXIO   = 0x0006,      // No such device or address
    EAGAIN  = 0x000B,      // Try again
    ENOMEM  = 0x000C,      // Out of memory
    EBUSY   = 0x0010,      // Resource is busy
    EINVAL  = 0x0016,      // Invalid argument
    ENODATA = 0x003D,      // No data available
    ETIME   = 0x003E,      // Timer expired

                           // Nonstandard errors below
    EINIT   = 0x00F0,      // Module failed to initialize
    UNUSED  = 0xFFFF       // For sizing the enum type
} err_t;

/** Mask for error reporting from a specific subsystem. */
typedef enum {
    ERR_ID_CMD_MODULE      = 0x0100,
    ERR_ID_LEDS_MODULE     = 0x0200,
    ERR_ID_GRAPHICS_MODULE = 0x0300,
    ERR_ID_SERVO_MODULE    = 0x0400,
    UNUSED_ID_MODULE       = 0xFFFF     // For sizing the enum type
} err_module_id_t;

/** Allowed logging levels. */
typedef enum {
    LOG_LEVEL_DEBUG = 0,
    LOG_LEVEL_INFO,
    LOG_LEVEL_WARNING,
    LOG_LEVEL_ERROR
} loglevel_t;

#ifndef LOG_LEVEL
    /** The loglevel for use by the whole system. */
    #define LOG_LEVEL INFO
#endif

extern err_t errno;

/** Debug logging. */
void log_debug(const char *str, ...);

/** Info logging. */
void log_info(const char *str, ...);

/** Warning logging. */
void log_warning(const char *str, ...);

/** Error logging. */
void log_error(const char *str, ...);

/** Set the errno from a particular subsystem. */
void set_errno(err_module_id_t module_id, err_t error);

#ifdef __cplusplus
}
#endif
