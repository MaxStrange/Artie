// Stdlib
#include <stdarg.h>
#include <stdio.h>
// Local includes
#include "errors.h"

#define CALL_LOG_FUNCTION() do { \
    va_list args; \
    va_start(args, str); \
    logging_internal(str, args); \
    va_end(args); \
} while (0)

static void logging_internal(const char *str, va_list args)
{
    printf(str, args);
}

void log_debug(const char *str, ...)
{
    #if LOG_LEVEL == LOG_LEVEL_DEBUG
    printf("[DEBUG]: ");
    CALL_LOG_FUNCTION();
    #endif // if LOG_LEVEL
}

void log_info(const char *str, ...)
{
    #if LOG_LEVEL <= LOG_LEVEL_INFO
    printf("[INFO]: ");
    CALL_LOG_FUNCTION();
    #endif // if LOG_LEVEL
}

void log_warning(const char *str, ...)
{
    #if LOG_LEVEL <= LOG_LEVEL_WARNING
    printf("[WARNING]: ");
    CALL_LOG_FUNCTION();
    #endif // if LOG_LEVEL
}

void log_error(const char *str, ...)
{
    #if LOG_LEVEL <= LOG_LEVEL_ERROR
    printf("[ERROR]: ");
    CALL_LOG_FUNCTION();
    #endif // if LOG_LEVEL
}

void set_errno(err_module_id_t module_id, err_t error)
{
    errno = module_id | error;
}
