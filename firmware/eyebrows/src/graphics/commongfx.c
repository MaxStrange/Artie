// Std lib includes
#include <stdio.h>
// SDK includes
// Local includes
#include "commongfx.h"
#include "lcd/LCD/LCD_1in14.h"
#include "lcd/LCD/LCD_2in.h"
#include "lcd/GUI/GUI_Paint.h"
#include "../board/errors.h"

/** Union of two functions since they have slightly different signatures. */
typedef union {
    void (*display_1in14)(UWORD *);
    void (*display_2in)(UBYTE *);
} lcd_display_function_t;

/** "Class" describing the LCD. */
typedef struct {
    UWORD width;
    UWORD height;
    void (*clear)(UWORD);
    void (*init)(UBYTE);
    lcd_display_function_t display;
} lcd_t;

static const lcd_display_function_t display_for_1in14_lcd = {.display_1in14 = &LCD_1IN14_Display};
static const lcd_display_function_t display_for_2in_lcd = {.display_2in = &LCD_2IN_Display};

/** If we are eyebrows, we use this LCD. */
static const lcd_t eyebrows_lcd = {
    .width = LCD_1IN14_WIDTH,
    .height = LCD_1IN14_HEIGHT,
    .clear = &LCD_1IN14_Clear,
    .init = &LCD_1IN14_Init,
    .display = display_for_1in14_lcd,
};

/** If we are mouth, we use this LCD. */
static const lcd_t mouth_lcd = {
    .width = LCD_2IN_WIDTH,
    .height = LCD_2IN_HEIGHT,
    .clear = &LCD_2IN_Clear,
    .init = &LCD_2IN_Init,
    .display = display_for_2in_lcd,
};

/** Cache the size of the LCD since it won't change at runtime after initialization. */
static lcd_t lcd = eyebrows_lcd;

/** Number of values in an LCD image */
#ifdef MOUTH
    #define IMAGE_SIZE (LCD_2IN_HEIGHT * LCD_2IN_WIDTH * 2)
    /** The buffer we paint into and send to the LCD for display */
    static UWORD *paint_buffer = NULL; // Too big for .bss; need to use heap
#else
    #define IMAGE_SIZE (LCD_1IN14_HEIGHT * LCD_1IN14_WIDTH * 2)
    /** The buffer we paint into and send to the LCD for display */
    static UWORD paint_buffer[IMAGE_SIZE];
#endif // MOUTH

static void init_paint_buffer(void)
{
#ifdef MOUTH
    if (paint_buffer == NULL)
    {
        // Allocate memory from the heap for paint buffer
        paint_buffer = (UWORD *)malloc(IMAGE_SIZE);
    }

    if (paint_buffer == NULL)
    {
        // If paint_buffer is still NULL, malloc failed.
        log_error("Failed to allocate paint buffer. LCD will be unavailable.\n");
        set_errno(ERR_ID_GRAPHICS_MODULE, ENOMEM);
        return;
    }
#endif // MOUTH

#ifdef MOUTH
    uint16_t rotate = ROTATE_270;
    Paint_NewImage((UBYTE *)paint_buffer, lcd.height, lcd.width, 90, WHITE);
#else
    uint16_t rotate = ROTATE_0;
    Paint_NewImage((UBYTE *)paint_buffer, lcd.width, lcd.height, 0, WHITE);
#endif // MOUTH
    Paint_SetScale(65);
    Paint_Clear(WHITE);
    Paint_SetRotate(rotate);
}

uint16_t gfx_lcd_width(void)
{
    return lcd.width;
}

uint16_t gfx_lcd_height(void)
{
    return lcd.height;
}

void gfx_send_paint_buffer_to_lcd(void)
{
    if (paint_buffer == NULL)
    {
        return;
    }
#ifdef MOUTH
    lcd.display.display_2in((uint8_t *)paint_buffer);
#else
    lcd.display.display_1in14(paint_buffer);
#endif // MOUTH
}

void gfx_lcd_reset(void)
{
    Paint_Clear(WHITE);
    lcd.clear(WHITE);

    // Create new buffer for when we want to turn back on
    init_paint_buffer();
}

void gfx_init(lcd_size_t lcdsz)
{
    uint8_t err = DEV_Module_Init();
    if (err != 0)
    {
        log_error("Error starting LCD: %d\n", err);
        set_errno(ERR_ID_GRAPHICS_MODULE, EINIT);
        return;
    }
    DEV_SET_PWM(50);

    switch (lcdsz)
    {
        case LCD_SIZE_EYEBROWS:
            {
                lcd = eyebrows_lcd;
            }
            break;
        case LCD_SIZE_MOUTH:
            {
                lcd = mouth_lcd;
            }
            break;
        default:
            log_error("Invalid LCD size: %d\n", lcdsz);
            set_errno(ERR_ID_GRAPHICS_MODULE, EINIT);
            break;
    }

    lcd.init(HORIZONTAL);
    lcd.clear(WHITE);
    init_paint_buffer();
}
