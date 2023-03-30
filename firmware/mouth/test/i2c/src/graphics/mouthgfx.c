#ifdef MOUTH
// Std lib includes
#include <stdio.h>
// SDK includes
// Local includes
#include "commongfx.h"
#include "lcd/LCD/LCD_2in.h"
#include "lcd/GUI/GUI_Paint.h"
#include "../cmds/cmds.h"
#include "../board/errors.h"

////////////////////////// All these values need to be determined through testing /////////////////////////
/** The width of the mouth. */
#define MOUTH_WIDTH 100

/** The x position of the left corner of the mouth. */
#define X_POS_LEFT_CORNER 25

#define X_POS_RIGHT_CORNER (X_POS_LEFT_CORNER + MOUTH_WIDTH)

/** The y position of the two corners of the mouth. */
#define Y_POS_CORNERS 75

/** The x position of the center of the mouth. */
#define X_POS_CENTER ((((X_POS_RIGHT_CORNER)) - ((X_POS_LEFT_CORNER))) / 2)
////////////////////////////////////////////////////////////////////////////////////////////////////////////

static void draw_mouth_smile(void)
{
    // Bottom half of a circle
    DRAW_CIRCLE(X_POS_CENTER, Y_POS_CORNERS, MOUTH_WIDTH/2);
    DRAW_FILLED_RECTANGLE(X_POS_LEFT_CORNER, Y_POS_CORNERS+(MOUTH_WIDTH/2), X_POS_RIGHT_CORNER, Y_POS_CORNERS+1);
    log_debug("Paint smile\n");
    gfx_send_paint_buffer_to_lcd();
}

static void draw_mouth_frown(void)
{
    // Top half of a circle, translated down so the top is at Y_POS_CORNERS
    DRAW_CIRCLE(X_POS_CENTER, Y_POS_CORNERS - (MOUTH_WIDTH/2), MOUTH_WIDTH/2);
    DRAW_FILLED_RECTANGLE(X_POS_LEFT_CORNER, Y_POS_CORNERS - (MOUTH_WIDTH/2), X_POS_RIGHT_CORNER, Y_POS_CORNERS - MOUTH_WIDTH);
    log_debug("Paint frown\n");
    gfx_send_paint_buffer_to_lcd();
}

static void draw_mouth_line(void)
{
    // Draw line
    DRAW_SOLID_LINE(X_POS_LEFT_CORNER, Y_POS_CORNERS, X_POS_RIGHT_CORNER, Y_POS_CORNERS);
    log_debug("Paint line\n");
    gfx_send_paint_buffer_to_lcd();
}

static void draw_mouth_smirk(void)
{
    // Draw a line
    DRAW_SOLID_LINE(X_POS_LEFT_CORNER, Y_POS_CORNERS, X_POS_RIGHT_CORNER, Y_POS_CORNERS);
    // Draw a small curve at the end of the line
    const UWORD rad = MOUTH_WIDTH / 6;
    DRAW_CIRCLE(X_POS_RIGHT_CORNER, Y_POS_CORNERS + (rad), rad);
    DRAW_FILLED_RECTANGLE(X_POS_RIGHT_CORNER - rad, Y_POS_CORNERS + (2 * rad), X_POS_RIGHT_CORNER + rad, Y_POS_CORNERS + rad);
    log_debug("Paint smirk\n");
    gfx_send_paint_buffer_to_lcd();
}

static void draw_mouth_zigzag(void)
{
    // Draw a bunch of lines, each of which starts at the end of the line previous
    uint8_t nzigs = 5;
    UWORD start_x = X_POS_LEFT_CORNER;
    UWORD start_y = Y_POS_CORNERS;
    const UWORD bottom_y = start_y - 25;
    UWORD end_x = start_x + (MOUTH_WIDTH / nzigs);
    UWORD end_y = bottom_y;
    bool down = true;
    for (uint8_t i = 0; i < nzigs; i++)
    {
        DRAW_SOLID_LINE(start_x, start_y, end_x, end_y);
        down = !down;
        start_x = end_x;
        start_y = end_y;
        end_x += (MOUTH_WIDTH / nzigs);
        end_y = down ? bottom_y : Y_POS_CORNERS;
    }
}

static void draw_mouth_open(void)
{
    // Draw a circle
    DRAW_CIRCLE(X_POS_CENTER, Y_POS_CORNERS, MOUTH_WIDTH/2);
    log_debug("Paint open\n");
    gfx_send_paint_buffer_to_lcd();
}

static void draw_mouth_open_smile(void)
{
    // Draw bottom half of a circle
    DRAW_CIRCLE(X_POS_CENTER, Y_POS_CORNERS, MOUTH_WIDTH/2);
    DRAW_FILLED_RECTANGLE(X_POS_LEFT_CORNER, Y_POS_CORNERS+(MOUTH_WIDTH/2), X_POS_RIGHT_CORNER, Y_POS_CORNERS+1);
    // Draw top line
    DRAW_SOLID_LINE(X_POS_LEFT_CORNER, Y_POS_CORNERS, X_POS_RIGHT_CORNER, Y_POS_CORNERS);
    log_debug("Paint open smile\n");
    gfx_send_paint_buffer_to_lcd();
}

void mouthgfx_init(void)
{
    gfx_init(LCD_SIZE_MOUTH);
}

void mouthgfx_cmd(cmd_t command)
{
    switch (command)
    {
        case CMD_LCD_TEST:
            gfx_draw_test();
            break;
        case CMD_LCD_OFF:
            gfx_lcd_reset();
            break;
        case CMD_LCD_MOUTH_SMILE:
            draw_mouth_smile();
            break;
        case CMD_LCD_MOUTH_FROWN:
            draw_mouth_frown();
            break;
        case CMD_LCD_MOUTH_LINE:
            draw_mouth_line();
            break;
        case CMD_LCD_MOUTH_SMIRK:
            draw_mouth_smirk();
            break;
        case CMD_LCD_MOUTH_OPEN:
            draw_mouth_open();
            break;
        case CMD_LCD_MOUTH_OPEN_SMILE:
            draw_mouth_open_smile();
            break;
        case CMD_LCD_MOUTH_ZIG_ZAG:
            draw_mouth_zigzag();
            break;
        default:
            log_error("Illegal cmd type 0x%02X\n in graphics subsystem\n", command);
            set_errno(ERR_ID_GRAPHICS_MODULE, EINVAL);
            break;
    }
}

#endif // MOUTH
