// Stdlib includes
#include <stdbool.h>
#include <stdio.h>
// SDK includes
#include "pico/stdlib.h"
// Local includes

int main()
{
    // Initialize UART for debugging (in a release build, this should be turned off from the CMake build system)
    stdio_init_all();

    while (true)
    {
        // TODO
        // Contract is this:
        //      Controller Module tells us who to reset, then we handle the reset logic asynchronously.
    }
}
