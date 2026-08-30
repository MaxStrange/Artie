// Std lib includes
// SDK includes
// Local includes
#include "../cmds/cmds.h"
#include "../board/errors.h"
#ifdef MOUTH
    #include "mouthgfx.h"
#else
    #include "eyebrowsgfx.h"
#endif // MOUTH

void graphics_init(side_t side)
{
    log_info("Init LCD\n");

#if MOUTH
    mouthgfx_init();
#else
    eyebrowsgfx_init(side);
#endif // MOUTH
}

void graphics_cmd(cmd_t command)
{
#if MOUTH
    mouthgfx_cmd(command);
#else
    eyebrowsgfx_cmd(command);
#endif // MOUTH
}
