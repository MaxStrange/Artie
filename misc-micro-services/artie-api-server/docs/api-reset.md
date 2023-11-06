# API for Reset Service

## Reset an MCU

Reset the given MCU. Please note that resetting an MCU may degrade Artie's abilities
for a short period of time.

* *POST*: `/reset/mcu`
    * *Parameters*:
        * `artie-id`: The Artie ID.
        * `id`: The MCU ID. See [MCU IDs](../README.md#mcu-ids) for the list of available MCU IDs.
    * *Payload*: None

## Reset an SBC

Reset the given SBC. Please note that SBCs may take several minutes to completely reboot,
and Artie service will be interrupted or degraded during that time.

* *POST*: `/reset/sbc`
    * *Parameters*:
        * `artie-id`: The Artie ID.
        * `id`: The SBC ID. See [SBC IDs](../README.md#sbc-ids) for the list of available SBC IDs.
    * *Payload*: None

## Get Status

Get the reset service's submodules' statuses.

* *GET*: `/reset/status`
    * *Parameters*:
        * `artie-id`: The Artie ID.
* *Response 200*:
    * *Payload (JSON)*:
        ```json
        {
            "artie-id": "The Artie ID.",
            "MCU": "<Status>"
        }
        ```
    where `<Status>` is one of the available
    status values as [found in the top-level API README](../README.md#statuses)

## Self Test

Initiate a self-test.

* *POST*: `/reset/self-test`
    * *Parameters*:
        * `artie-id`: The Artie ID.
    * *Payload*: None
