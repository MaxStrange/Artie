// Std lib includes
#include <stdio.h>
// SDK includes
#include "pico/multicore.h"
#include "pico/util/queue.h"
// Local includes
#include "commongfx.h"
#include "lcd/LCD/LCD_1in14.h"
#include "lcd/GUI/GUI_Paint.h"
#include "../cmds/cmds.h"
#include "../board/errors.h"

/** The location of a given pair of vertices */
typedef enum {
    VERTEX_POS_LOW = 0,
    VERTEX_POS_MIDDLE = 1,
    VERTEX_POS_HIGH = 2
} vertex_pos_t;

/** The eyebrow that we draw. */
typedef struct {
    vertex_pos_t left;
    vertex_pos_t middle;
    vertex_pos_t right;
} eyebrow_t;

/** The current state of the eyebrow. */
static eyebrow_t eyebrow_state = {
    .left = VERTEX_POS_MIDDLE,
    .middle = VERTEX_POS_MIDDLE,
    .right = VERTEX_POS_MIDDLE
};

/** The pixel X location of left vertices. */
static const UWORD X_POS_LEFT_VERTEX = 25;

/** The pixel X location of middle vertices. */
static const UWORD X_POS_MIDDLE_VERTEX = 115;

/** The pixel X location of right vertices. */
static const UWORD X_POS_RIGHT_VERTEX = 200;

/** The Y offsets to apply when in VERTEX_POS_LOW, VERTEX_POS_MIDDLE, or VERTEX_POS_HIGH */
static const UWORD LOOKUP_Y_OFFSETS[] = {50, 25, 0};

/** The starting Y value for any vertex. Apply an offset from LOOKUP_Y_OFFSETS. */
static const UWORD Y_POS_BASE = 25;

/** The thickness of the eyebrow. */
static const UWORD EYEBROW_Y_THICKNESS = 50;

/** Macro for looking up bottom left y position at runtime. */
#define BOTTOM_LEFT_Y() Y_POS_BASE + LOOKUP_Y_OFFSETS[eyebrow_state.left] + EYEBROW_Y_THICKNESS

/** Macro for looking up bottom middle y position at runtime. */
#define BOTTOM_MIDDLE_Y() Y_POS_BASE + LOOKUP_Y_OFFSETS[eyebrow_state.middle] + EYEBROW_Y_THICKNESS

/** Macro for looking up bottom right y position at runtime. */
#define BOTTOM_RIGHT_Y() Y_POS_BASE + LOOKUP_Y_OFFSETS[eyebrow_state.right] + EYEBROW_Y_THICKNESS

/** Macro for looking up top left y position at runtime. */
#define TOP_LEFT_Y() Y_POS_BASE + LOOKUP_Y_OFFSETS[eyebrow_state.left]

/** Macro for looking up top middle y position at runtime. */
#define TOP_MIDDLE_Y() Y_POS_BASE + LOOKUP_Y_OFFSETS[eyebrow_state.middle]

/** Macro for looking up top right y position at runtime. */
#define TOP_RIGHT_Y() Y_POS_BASE + LOOKUP_Y_OFFSETS[eyebrow_state.right]

/** A buffer for putting strings into. */
static char strbuf[32];

/** Smallish value for commands to be fed into the LCD command queue by the main core. */
#define INTER_CORE_QUEUE_SIZE 32

/** Inter-core communication queue. */
static queue_t inter_core_queue;

/** Which side eye are we (left/right)? */
static side_t left_or_right_side = EYE_UNASSIGNED_SIDE;

/** Put the current eyebrow state into a string buffer. */
static void eyebrow_state_to_strbuf(size_t n, char *buf)
{
    ssize_t nleft = n;
    size_t offset = 0;
    int nwritten = 0;
    for (size_t i = 0; i < 3; i++)
    {
        vertex_pos_t pos = (i == 0) ? eyebrow_state.left : ((i == 1) ? eyebrow_state.middle : eyebrow_state.right);
        switch (pos)
        {
            case VERTEX_POS_LOW:
                assert(offset < n);
                nwritten = snprintf(buf + offset, nleft, " LOW");
                offset += nwritten; // Overwrite null pointer with next print
                nleft -= nwritten;
                break;
            case VERTEX_POS_MIDDLE:
                assert(offset < n);
                nwritten = snprintf(buf + offset, nleft, " MID");
                offset += nwritten;
                nleft -= nwritten;
                break;
            case VERTEX_POS_HIGH:
                assert(offset < n);
                nwritten = snprintf(buf + offset, nleft, " HIGH");
                offset += nwritten;
                nleft -= nwritten;
                break;
            default:
                log_error("Error understanding vertex position %d: Value is %d", i, pos);
                break;
        }
    }
    buf[offset] = '\0';
}

static void log_eyebrow_state(void)
{
    log_debug("LCD: Eyebrow state:");
    eyebrow_state_to_strbuf(count_of(strbuf), strbuf);
    printf(strbuf);
    printf("\n");
}

/** Label each point on the LCD for debugging purposes. Does not refresh LCD, simply paints to the current buffer. */
static void label_points(void)
{
    DRAW_TEXT(X_POS_LEFT_VERTEX, BOTTOM_LEFT_Y(), "BL");
    DRAW_TEXT(X_POS_LEFT_VERTEX, TOP_LEFT_Y(), "TL");
    DRAW_TEXT(X_POS_MIDDLE_VERTEX, BOTTOM_MIDDLE_Y(), "BM");
    DRAW_TEXT(X_POS_MIDDLE_VERTEX, TOP_MIDDLE_Y(), "TM");
    DRAW_TEXT(X_POS_RIGHT_VERTEX, BOTTOM_RIGHT_Y(), "BR");
    DRAW_TEXT(X_POS_RIGHT_VERTEX, TOP_RIGHT_Y(), "TR");
}

static void paint_eyebrow(void)
{
    gfx_lcd_reset();

    // Eyebrow is composed of six vertices:
    //  Top Left, Top Middle, Top Right
    //  Btm Left, Btm Middle, Btm Right
    //
    // There is a line connecting them like this:
    //
    //     * ------- * --------- *
    //     |                     |
    //     * ------- * --------- *

    UWORD y0;
    UWORD y1;

    // Paint line from bottom left -> top left
    DRAW_SOLID_LINE(X_POS_LEFT_VERTEX, BOTTOM_LEFT_Y(), X_POS_LEFT_VERTEX, TOP_LEFT_Y());

    // Paint line from top left -> top middle
    DRAW_SOLID_LINE(X_POS_LEFT_VERTEX, TOP_LEFT_Y(), X_POS_MIDDLE_VERTEX, TOP_MIDDLE_Y());

    // Paint line from top middle -> top right
    DRAW_SOLID_LINE(X_POS_MIDDLE_VERTEX, TOP_MIDDLE_Y(), X_POS_RIGHT_VERTEX, TOP_RIGHT_Y());

    // Paint line from top right -> bottom right
    DRAW_SOLID_LINE(X_POS_RIGHT_VERTEX, TOP_RIGHT_Y(), X_POS_RIGHT_VERTEX, BOTTOM_RIGHT_Y());

    // Paint line from bottom left -> bottom middle
    DRAW_SOLID_LINE(X_POS_LEFT_VERTEX, BOTTOM_LEFT_Y(), X_POS_MIDDLE_VERTEX, BOTTOM_MIDDLE_Y());

    // Paint line from bottom middle -> bottom right
    DRAW_SOLID_LINE(X_POS_MIDDLE_VERTEX, BOTTOM_MIDDLE_Y(), X_POS_RIGHT_VERTEX, BOTTOM_RIGHT_Y());

    // Send buffer to LCD
    gfx_send_paint_buffer_to_lcd();
}

static void draw(cmd_t command)
{
    // Mask off first two bits, these are the subsystem mask
    uint8_t cmd_param = command & 0x3F;

    // Assert that for each of the 3 msbs (which are set) of the six bit value,
    // the corresponding lsb (of the 3 bottom lsbs) is cleared.
    // If it is not, it should be a special command, like test or off,
    // and we shouldn't be handling it here.
    // See the graphics_cmd schema in the header file for details.
    for (size_t i = 0; i < 3; i++)
    {
        // Is the msb set?
        if (0x08 & (cmd_param >> i))
        {
            // Is the lsb set?
            if (0x01 & (cmd_param >> i))
            {
                log_error("Illegal command in LCD subsystem: 0x%02X with param: 0x%02X\n", command);
                set_errno(ERR_ID_GRAPHICS_MODULE, EINVAL);
                return;
            }
        }
    }

    static uint8_t msbs[3];
    static uint8_t lsbs[3];
    assert(count_of(msbs) == count_of(lsbs));
    for (size_t i = 0; i < count_of(msbs); i++)
    {
        if (0x08 & (cmd_param >> i))
        {
            // msb is set
            // Set this vertex pair to middle
            msbs[i] = 1;
            lsbs[i] = 0;
        }
        else if (0x01 & (cmd_param >> i))
        {
            // lsb is set
            // Set this vertex pair to high
            msbs[i] = 0;
            lsbs[i] = 1;
        }
        else
        {
            // neither set
            // Set this vertex pair to low
            msbs[i] = 0;
            lsbs[i] = 0;
        }
    }

    // If we are the right side, we need to reverse some bits,
    // as this algorithm was written for the left side originally.
    if (left_or_right_side == EYE_RIGHT_SIDE)
    {
        // Swap left and right on msbs
        uint8_t tmp = msbs[0];
        msbs[0] = msbs[2];
        msbs[2] = tmp;

        // Swap left and right on lsbs
        tmp = lsbs[0];
        lsbs[0] = lsbs[2];
        lsbs[2] = tmp;
    }

    // Turn the bit manipulation results into a struct
    eyebrow_state.left    = (msbs[0] ? VERTEX_POS_MIDDLE : (lsbs[0] ? VERTEX_POS_HIGH : VERTEX_POS_LOW));
    eyebrow_state.middle  = (msbs[1] ? VERTEX_POS_MIDDLE : (lsbs[1] ? VERTEX_POS_HIGH : VERTEX_POS_LOW));
    eyebrow_state.right   = (msbs[2] ? VERTEX_POS_MIDDLE : (lsbs[2] ? VERTEX_POS_HIGH : VERTEX_POS_LOW));

    log_eyebrow_state();

    // Paint the new state
    paint_eyebrow();
}

static void core_task(void)
{
    gfx_init(LCD_SIZE_EYEBROWS);

    // Left eyebrow LCD is installed upside-down
    if (left_or_right_side == EYE_LEFT_SIDE)
    {
        Paint_SetRotate(ROTATE_180);
    }
    else
    {
        Paint_SetRotate(ROTATE_0);
    }
    Paint_Clear(WHITE);

    while (true)
    {
        cmd_t command;
        queue_remove_blocking(&inter_core_queue, &command);
        switch (command)
        {
            case CMD_LCD_OFF:
                log_debug("LCD: off\n");
                gfx_lcd_reset();
                break;
            case CMD_LCD_TEST:
                log_debug("LCD: test\n");
                gfx_draw_test();
                break;
            default:
                {
                    if ((command & 0xC0) != CMD_MODULE_ID_LCD)
                    {
                        log_error("Illegal cmd type 0x%02X\n in graphics subsystem\n", command);
                    }
                    else
                    {
                        log_debug("LCD: Draw\n");
                        draw(command);
                    }
                }
                break;
        }
    }
}

void eyebrowsgfx_init(side_t side)
{
    // Set the module-level variable to tell us which side we are (left or right)
    left_or_right_side = side;

    // Initialize the inter-core queue with a mutex to be safe.
    static const uint SPINLOCK_ID = 0; // If we need more than one of these, we should put them all in the same header.
    queue_init_with_spinlock(&inter_core_queue, sizeof(cmd_t), INTER_CORE_QUEUE_SIZE, SPINLOCK_ID);

    // Start up the task for the other core
    multicore_launch_core1(core_task);
}

void eyebrowsgfx_cmd(cmd_t command)
{
    // This function is called from the main thread's core.
    // Submit the work item to the other core for processing and return.
    bool added = queue_try_add(&inter_core_queue, &command);
    if (!added)
    {
        log_error("LCD: Could not add command to work queue. Queue is full.\n");
    }
}
