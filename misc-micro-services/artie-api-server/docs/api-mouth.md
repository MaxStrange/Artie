# API for Mouth Module

Available mouth displays:

* `smile`
* `frown`
* `line`
* `smirk`
* `open`
* `open-smile`
* `zig-zag`
* `talking`: Sets the mouth to talking mode, where it opens and closes until the display is told to do something else.

## Change Mouth Display

Change the mouth display to show the given state.

* *POST*: `/mouth/lcd`
    * *Parameters*:
        * `artie-id`: The Artie ID.
        * `display`: One of the [available display values](#mouth)
    * *Payload*: None

## Get Mouth Display

* *GET*: `/mouth/lcd`
    * *Parameters*:
        * `artie-id`: The Artie ID.
* *Response 200*:
    * *Payload (JSON)*:
        ```json
        {
            "artie-id": "The Artie ID.",
            "display": "One of the available display values"
        }
        ```

## Test Mouth LCD

Draw a test image on the mouth LCD.

* *POST*: `/mouth/lcd/test`
    * *Parameters*:
        * `artie-id`: The Artie ID.
    * *Payload*: None

## Clear Mouth LCD

Erase the contents on the mouth LCD.

* *POST*: `/mouth/lcd/off`
    * *Parameters*:
        * `artie-id`: The Artie ID.
    * *Payload*: None

## Update Mouth LED State

* *POST*: `/mouth/led`
    * *Parameters*:
        * `artie-id`: The Artie ID.
        * `state`: One of `on`, `off`, or `heartbeat`
    * *Payload*: None

## Get Mouth LED State

* *GET*: `/mouth/led`
    * *Parameters*:
        * `artie-id`: The Artie ID.
* *Response 200*:
    * *Payload (JSON)*:
        ```json
        {
            "artie-id": "The Artie ID.",
            "state": "on, off, or heartbeat"
        }
        ```

## Reload Mouth Firmware

Reload MCU firmware.

* *POST*: `/mouth/fw`
    * *Parameters*:
        * `artie-id`: The Artie ID.
    * *Payload*: None
