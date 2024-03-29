# Revisions

## Rev 0.2

* This is the circuit board you need for Artie Aardvark.
* This is a Raspberry Pi Hat which should have female pins soldered to the *underside of the board*,
  then the board should be slotted onto the RPi itself.
* The micro USB adapter is for a serial (UART) connection to the Raspberry Pi.
* No need to supply any power to the Raspberry Pi itself.
  Power is supplied by means of the [head's power rail board](../head-power-rail/REVISIONS.md).

## Rev 0.1

* This is a Raspberry Pi Hat which should have female pins soldered to the *underside of the board*,
  then the board should be slotted onto the RPi itself.
* Supply 9V to this board through the barrel jack *in addition to supplying power to the RPi's USB C adapter*.
  This power supply is for all the peripherals in Artie's head. It does not supply the power to the RPi,
  nor do any of the peripherals draw power from the RPi directly.
    * **This is fixed in the second rev**.
* The micro USB adapter is for a serial (UART) connection to the Raspberry Pi.
