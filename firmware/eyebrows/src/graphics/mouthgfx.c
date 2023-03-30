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

/** The width of the mouth. */
#define MOUTH_WIDTH 275

/** The x position of the left corner of the mouth. */
#define X_POS_LEFT_CORNER 20

#define X_POS_RIGHT_CORNER (X_POS_LEFT_CORNER + MOUTH_WIDTH)

/** The y position of the two corners of the mouth. */
#define Y_POS_CORNERS 120

/** The x position of the center of the mouth. */
#define X_POS_CENTER (X_POS_LEFT_CORNER + (MOUTH_WIDTH / 2))

/** Are we currently in a talking state? */
static volatile bool talking = false;

/** Repeating timer used by talking stuff. */
static repeating_timer_t timer;

static void draw_line_no_erase(void)
{
    DRAW_SOLID_LINE(X_POS_LEFT_CORNER, Y_POS_CORNERS, X_POS_RIGHT_CORNER, Y_POS_CORNERS);
    log_debug("Paint line\n");
    gfx_send_paint_buffer_to_lcd();
}

static void erase_line(void)
{
    ERASE_SOLID_LINE(X_POS_LEFT_CORNER, Y_POS_CORNERS, X_POS_RIGHT_CORNER, Y_POS_CORNERS);
}

static void draw_open_no_erase(void)
{
    // Draw a circle
    DRAW_CIRCLE(X_POS_CENTER, Y_POS_CORNERS, MOUTH_WIDTH/4);
    log_debug("Paint open\n");
    gfx_send_paint_buffer_to_lcd();
}

static void erase_open(void)
{
    ERASE_CIRCLE(X_POS_CENTER, Y_POS_CORNERS, MOUTH_WIDTH/4);
}

static inline bool talking_cb(repeating_timer_t *rt)
{
    if (!talking)
    {
        // Somehow we got called even though we should be turned off.
        // Abort and cancel timer.
        return false;
    }

    static bool mouth_open = false;
    if (mouth_open)
    {
        // Draw mouth closed
        mouth_open = false;
        erase_open();
        draw_line_no_erase();
    }
    else
    {
        // Draw mouth open
        mouth_open = true;
        erase_line();
        draw_open_no_erase();
    }

    return true;
}

static void start_talking(void)
{
    Paint_Clear(WHITE);

    // Fire off a timer that will trigger a periodic interrupt to refresh the LCD
    const int32_t refresh_period_ms = 1000;
    talking = true;
    bool worked = add_repeating_timer_ms(refresh_period_ms, &talking_cb, NULL, &timer);
    if (!worked)
    {
        set_errno(ERR_ID_GRAPHICS_MODULE, ENOMEM);
        log_error("Could not initialize repeating timer for talking animation.\n");
    }
}

static void stop_talking(void)
{
    // Disable the talking timer/interrupt
    if (talking)
    {
        talking = false;
        bool worked = cancel_repeating_timer(&timer);
        if (!worked)
        {
            set_errno(ERR_ID_GRAPHICS_MODULE, ENOENT);
            log_error("Could not cancel the repeating timer for some reason.\n");
        }
        Paint_Clear(WHITE);
    }
}

static void draw_mouth_smile(void)
{
    stop_talking();
    Paint_Clear(WHITE);

    // Bottom half of a circle
    uint16_t radius = MOUTH_WIDTH / 2;
    DRAW_CIRCLE(X_POS_CENTER, Y_POS_CORNERS - (radius / 4), radius);
    ERASE_RECTANGLE(0, 0, X_POS_RIGHT_CORNER, Y_POS_CORNERS-1);
    log_debug("Paint smile\n");
    gfx_send_paint_buffer_to_lcd();
}

static void draw_mouth_frown(void)
{
    stop_talking();
    Paint_Clear(WHITE);

    // Top half of a circle, translated down so the top is at Y_POS_CORNERS
    uint16_t radius = MOUTH_WIDTH / 2;
    DRAW_CIRCLE(X_POS_CENTER, Y_POS_CORNERS + (radius / 4), radius);
    ERASE_RECTANGLE(X_POS_LEFT_CORNER, Y_POS_CORNERS + 1, gfx_lcd_width(), gfx_lcd_height());
    log_debug("Paint frown\n");
    gfx_send_paint_buffer_to_lcd();
}

static void draw_mouth_line(void)
{
    stop_talking();
    Paint_Clear(WHITE);
    draw_line_no_erase();
}

static void draw_mouth_smirk(void)
{
    const UWORD rad = MOUTH_WIDTH / 6;

    stop_talking();
    Paint_Clear(WHITE);

    // Draw a line
    DRAW_SOLID_LINE(X_POS_LEFT_CORNER, Y_POS_CORNERS, X_POS_RIGHT_CORNER - rad, Y_POS_CORNERS);

    // Draw a small curve at the end of the line
    DRAW_CIRCLE(X_POS_RIGHT_CORNER - rad, Y_POS_CORNERS - rad, rad);
    ERASE_RECTANGLE(0, 0, gfx_lcd_width(), Y_POS_CORNERS - rad);
    ERASE_RECTANGLE(X_POS_RIGHT_CORNER - (2 * rad), Y_POS_CORNERS - (2 * rad), X_POS_RIGHT_CORNER - rad, Y_POS_CORNERS - (LINE_WIDTH + 1));
    log_debug("Paint smirk\n");
    gfx_send_paint_buffer_to_lcd();
}

static void draw_mouth_zigzag(void)
{
    stop_talking();
    Paint_Clear(WHITE);

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
    gfx_send_paint_buffer_to_lcd();
}

static void draw_mouth_open(void)
{
    stop_talking();
    Paint_Clear(WHITE);
    draw_open_no_erase();
}

static void draw_mouth_open_smile(void)
{
    stop_talking();
    Paint_Clear(WHITE);

    // Draw bottom half of a circle
    uint16_t up = 10;
    uint16_t radius = MOUTH_WIDTH / 2;
    DRAW_CIRCLE(X_POS_CENTER, Y_POS_CORNERS - (radius / 4), radius);
    ERASE_RECTANGLE(0, 0, X_POS_RIGHT_CORNER, (Y_POS_CORNERS-1) - up);

    // Draw top line
    DRAW_SOLID_LINE(X_POS_LEFT_CORNER + 1, Y_POS_CORNERS - up, X_POS_RIGHT_CORNER - 1, Y_POS_CORNERS - up);
    log_debug("Paint open smile\n");
    gfx_send_paint_buffer_to_lcd();
}

static void draw_test(void)
{
    stop_talking();
    gfx_lcd_reset();

    // Label left corner of the mouth
    Paint_DrawPoint(X_POS_LEFT_CORNER, Y_POS_CORNERS, BLACK, LINE_WIDTH, DOT_FILL_RIGHTUP);
    DRAW_TEXT(X_POS_LEFT_CORNER, Y_POS_CORNERS, "L");

    // Label right corner of the mouth
    Paint_DrawPoint(X_POS_RIGHT_CORNER, Y_POS_CORNERS, BLACK, LINE_WIDTH, DOT_FILL_RIGHTUP);
    DRAW_TEXT(X_POS_RIGHT_CORNER, Y_POS_CORNERS, "R");

    // Label the center of the mouth
    Paint_DrawPoint(X_POS_CENTER, Y_POS_CORNERS, BLACK, LINE_WIDTH, DOT_FILL_RIGHTUP);
    DRAW_TEXT(X_POS_CENTER, Y_POS_CORNERS, "C");

    // Send buffer to LCD
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
            draw_test();
            break;
        case CMD_LCD_OFF:
            stop_talking();
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
        case CMD_LCD_MOUTH_TALK:
            start_talking();
            break;
        default:
            log_error("Illegal cmd type 0x%02X\n in graphics subsystem\n", command);
            set_errno(ERR_ID_GRAPHICS_MODULE, EINVAL);
            break;
    }
}

#endif // MOUTH
