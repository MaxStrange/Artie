# API for Eyebrow Module

Eyebrows states are given as a tuple of three items per eyebrow: L/M/H x3.

For example:

* HHH: A line that is raised
* MHM: A line that looks like a ^
* LHL: Same as MHM, but sharper (edges are lower)
* LLL: A line that is low
* MMM: A line across the middle

## Change Eyebrow Display

Change the eyebrow display to show the given state.

* *POST*: `/eyebrows/lcd/<which>` where `<which>` is `left` or `right`.
    * *Parameters*:
        * `artie-id`: The Artie ID.
    * *Payload (JSON)*:
        ```json
        {
            "vertices": ["H/M/L", "H/M/L", "H/M/L"]
        }
        ```

## Get Eyebrow Display

* *GET*: `/eyebrows/lcd/<which>` where `<which>` is `left` or `right`.
    * *Parameters*:
        * `artie-id`: The Artie ID.
* *Response 200*:
    * *Payload (JSON)*:
        ```json
        {
            "artie-id": "The Artie ID.",
            "eyebrow-side": "left or right",
            "vertices": ["H/M/L", "H/M/L", "H/M/L"] OR "test" OR "clear" or "error"
        }
        ```

## Test an Eyebrow LCD

Draw a test image on the eyebrow LCD.

* *POST*: `/eyebrows/lcd/<which>/test` where `<which>` is `left` or `right`
    * *Parameters*:
        * `artie-id`: The Artie ID.
    * *Payload*: None

## Clear an Eyebrow LCD

Erase the contents on an eyebrow LCD.

* *POST*: `/eyebrows/lcd/<which>/off` where `<which>` is `left` or `right`
    * *Parameters*:
        * `artie-id`: The Artie ID.
    * *Payload*: None

## Update Eyebrow LED State

* *POST*: `/eyebrows/led/<which>` where `<which>` is `left` or `right`.
    * *Parameters*:
        * `artie-id`: The Artie ID.
        * `state`: One of `on`, `off`, or `heartbeat`
    * *Payload*: None

## Get Eyebrow LED State

* *GET*: `/eyebrows/led/<which>` where `<which>` is `left` or `right`.
    * *Parameters*:
        * `artie-id`: The Artie ID.
* *Response 200*:
    * *Payload (JSON)*:
        ```json
        {
            "artie-id": "The Artie ID.",
            "eyebrow-side": "left or right",
            "state": "on, off, or heartbeat"
        }
        ```

## Update Eyeball Servo Positions

* *POST*: `/eyebrows/servo/<which>` where `<which>` is `left` or `right`.
    * *Parameters*:
        * `artie-id`: The Artie ID.
        * `degrees`: The position to go to. Should be a degree (float) value within the closed range [0, 180]. 0 degrees is left. 180 degrees is right. 90 degrees is center.
    * *Payload*: None

## Get Eyeball Servo Positions

Note: there is no way to get a *true* servo position for the eyeballs
(at least in this version of Artie). The servos do not have
encoders that can be accessed. Instead, eye position should be
inferred by a higher layer that makes use of field of view
changes. This GET request simply returns the value that
the eyebrow driver *believes* the servo is currently at,
which will typically be the value that it was last set to (or its starting value).

* *GET*: `/eyebrows/servo/<which>` where `<which>` is `left` or `right`.
    * *Parameters*:
        * `artie-id`: The Artie ID.
* *Response 200*:
    * *Payload (JSON)*:
        ```json
        {
            "artie-id": "The Artie ID.",
            "eyebrow-side": "left or right",
            "degrees": "floating point value between 0 (left) and 180 (right)"
        }
        ```

## Reload Eyebrow Firmware

Reload both eyebrow MCU firmwares (you cannot target them individually).

* *POST*: `/eyebrows/fw`
    * *Parameters*:
        * `artie-id`: The Artie ID.
    * *Payload*: None

## Get Status

Get the eyebrows' submodules' statuses.

* *GET*: `/eyebrows/status`
    * *Parameters*:
        * `artie-id`: The Artie ID.
* *Response 200*:
    * *Payload (JSON)*:
        ```json
        {
            "artie-id": "The Artie ID.",
            "FW": "<Status>",
            "LED-LEFT": "<Status>",
            "LED-RIGHT": "<Status>",
            "LCD-LEFT": "<Status>",
            "LCD-RIGHT": "<Status>",
            "LEFT-SERVO": "<Status>",
            "RIGHT-SERVO": "<Status>"
        }
        ```

## Self Test

Initiate a self-test.

* *POST*: `/eyebrows/self-test`
    * *Parameters*:
        * `artie-id`: The Artie ID.
    * *Payload*: None
