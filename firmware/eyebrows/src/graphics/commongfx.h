/**
 * @file commongfx.h
 * @brief Stuff that is common between the mouth and eyebrow LCD subsystems.
 *
 */
#pragma once

#ifdef __cplusplus
extern "C" {
#endif

/** The possible sizes of LCD. */
typedef enum {
    LCD_SIZE_EYEBROWS,
    LCD_SIZE_MOUTH,
} lcd_size_t;

//#define LINE_WIDTH DOT_PIXEL_2X2
#define LINE_WIDTH DOT_PIXEL_4X4

/** Macro for drawing a circle centered at (x_center, y_center) with given radius. */
#define DRAW_CIRCLE(x_center, y_center, radius) Paint_DrawCircle((x_center), (y_center), (radius), BLACK, LINE_WIDTH, DRAW_FILL_EMPTY)

/** Macro for erasing a circle centered at (x_center, y_center) with given radius. */
#define ERASE_CIRCLE(x_center, y_center, radius) Paint_DrawCircle((x_center), (y_center), (radius), WHITE, LINE_WIDTH, DRAW_FILL_EMPTY)

/** Macro for drawing a filled rectangle at (top_left_x, top_left_y) to (bottom_right_x, bottom_right_y). */
#define ERASE_RECTANGLE(x0, y0, x1, y1) Paint_DrawRectangle((x0), (y0), (x1), (y1), WHITE, LINE_WIDTH, DRAW_FILL_FULL)

/** Macro for drawing a line from x0, y0 to x1, y1 */
#define DRAW_SOLID_LINE(x0, y0, x1, y1) Paint_DrawLine((x0), (y0), (x1), (y1), BLACK, LINE_WIDTH, LINE_STYLE_SOLID)

/** Macro for erasing a line from x0, y0 to x1, y1 */
#define ERASE_SOLID_LINE(x0, y0, x1, y1) Paint_DrawLine((x0), (y0), (x1), (y1), WHITE, LINE_WIDTH, LINE_STYLE_SOLID)

/** Macro for drawing text at a given point. */
#define DRAW_TEXT(x, y, str) Paint_DrawString_EN((x), (y), (str), &Font20, BLACK, WHITE)

/** Initialize the common GFX subsystem. */
void gfx_init(lcd_size_t lcdsz);

/** Reset the graphics stack. */
void gfx_lcd_reset(void);

/** Get the width of the LCD. */
uint16_t gfx_lcd_width(void);

/** Get the height of the LCD. */
uint16_t gfx_lcd_height(void);

/** Display the current paint buffer on the LCD. */
void gfx_send_paint_buffer_to_lcd(void);

#ifdef __cplusplus
}
#endif
