# Bill of Materials

Some parts just can't be built :disappointed:

Here's the list of things you have to buy. I try to keep this as up-to-date as possible.

## Artie Aardvark

### Controller Module

Electrical schematics and datasheets found here: [controller-module](../../electrical-schematics/controller-module/REVISIONS.md)

* [Raspberry Pi 4B](https://www.raspberrypi.com/products/raspberry-pi-4-model-b/)
* [Micro SD Card](https://www.adafruit.com/product/2693) - You just need one that is > 4 GB in size.
* [Circuit Board](../../electrical-schematics/controller-module/REVISIONS.md) - see [procuring the circuit boards](./building-artie-main.md#get-the-circuit-boards)
* [FTDI Breakout Board](https://www.sparkfun.com/products/13263) - NOTE: You do NOT need to cut the trace on the back/solder the jumper.
  The default TTL output for this chip is 3.3V. The jumper on the back just changes the Vout, which we don't use.
    * You'll need some [header pins](https://www.sparkfun.com/products/116) as well (you may as well buy a bunch of these)
* [RPi Pin Headers](https://www.adafruit.com/product/2222) - solder these to the *underside* of the board!
* 2x [10 pin Female Header](https://www.sparkfun.com/products/8506)
* [Extra Long Male Headers](https://www.adafruit.com/product/400)
* [Water cooling block (copper)](https://www.amazon.com/Wendry-Suitable-Graphics-Diameter-Internal/dp/B07WH4VRW6/ref=sr_1_2?crid=3A4AK84O663QT&keywords=40mm+copper+water+block&qid=1680746922&sprefix=40mm+copper+water+block%2Caps%2C155&sr=8-2) - 40 x 40 x 10 mm
* [Water cooling block (aluminum)](https://www.amazon.com/dp/B07FTWWVDV/ref=sspa_dk_detail_2?psc=1&pf_rd_p=08ba9b95-1385-44b0-b652-c46acdff309c&pf_rd_r=92DHAX775TENDZK8526T&pd_rd_wg=22JSH&pd_rd_w=R9AwY&content-id=amzn1.sym.08ba9b95-1385-44b0-b652-c46acdff309c&pd_rd_r=e6e1ab6b-7cde-4f4d-83d5-191e2ff36299&s=pc&sp_csd=d2lkZ2V0TmFtZT1zcF9kZXRhaWxfdGhlbWF0aWM&spLa=ZW5jcnlwdGVkUXVhbGlmaWVyPUEzVlZLS0lJWFZMRkRYJmVuY3J5cHRlZElkPUEwMTQ2ODM2M1Q0MlJUV1ZFSkhMMSZlbmNyeXB0ZWRBZElkPUEwMzY0Mjg2M0UxOFk0SFMyWEQ0USZ3aWRnZXROYW1lPXNwX2RldGFpbF90aGVtYXRpYyZhY3Rpb249Y2xpY2tSZWRpcmVjdCZkb05vdExvZ0NsaWNrPXRydWU=) - 40 x 40 x 12 mm
* [2x5 Male Header](https://www.sparkfun.com/products/8506)
* [2x5 Ribbon Cable](https://www.sparkfun.com/products/8535)
* [2x3 Male Header](https://www.sparkfun.com/products/10877)
* [2x3 Ribbon Cable](https://www.digikey.com/en/products/detail/samtec-inc/IDSD-03-D-06-00-T/3476372)
* [2x10 Male Header](https://www.digikey.com/en/products/detail/sullins-connector-solutions/SBH11-PBPC-D10-ST-BK/1990065)
* [2x10 Ribbon Cable](https://www.digikey.com/en/products/detail/cnc-tech/L3DDH-2006N/9867499)
* Through hole LED (whatever color you want) - radial, 3mm
* 1x 330 Ohm through hole resistor
* 2x 4.7kOhm through hole resistors
* 1x 1N4001 through hole diode

### Head CAN Bus Board

Electrical schematics and datasheets found here: [head-can-bus-board](../../electrical-schematics/head-can-bus-board/REVISIONS.md)

* [Circuit Board](../../electrical-schematics/head-can-bus-board/REVISIONS.md) - see [procuring the circuit boards](./building-artie-main.md#get-the-circuit-boards)
* 4x [CAN Modules](https://modtronix.com/product/im1can/) - TODO: product code
* 2x [2x20 Ribbon Cables](https://www.sparkfun.com/products/13028) for connecting to Jetsons.
* 2x [Female 40 pin headers](https://www.sparkfun.com/products/13054)
* [2x5 Male Header](https://www.sparkfun.com/products/8506) - for connecting to the power board
* [2x5 Ribbon Cable](https://www.sparkfun.com/products/8535)
* 2x [2x3 Male Header](https://www.sparkfun.com/products/10877)
* 2x [2x3 Ribbon Cable](https://www.digikey.com/en/products/detail/samtec-inc/IDSD-03-D-06-00-T/3476372)
* TODO: CAN cabling

### SWD Board

Electrical schematics and datasheets found here: [swd-board](../../electrical-schematics/swd-board/REVISIONS.md)

* 4x [CD74HC237 Demux Chip](https://www.digikey.com/en/products/detail/texas-instruments/CD74HC237E/1506851) -
  for demuxing RESET line to each chip.
* [Raspberry Pi Pico](https://www.adafruit.com/product/5525)
* [2x20 Ribbon Cable](https://www.sparkfun.com/products/13028)
* [Female 40 pin header](https://www.sparkfun.com/products/13054)
* [2x10 Male Header](https://www.digikey.com/en/products/detail/sullins-connector-solutions/SBH11-PBPC-D10-ST-BK/1990065)
* [2x10 Ribbon Cable](https://www.digikey.com/en/products/detail/cnc-tech/L3DDH-2006N/9867499)
* 3x [2x5 Male Headers](https://www.sparkfun.com/products/8506)
* 3x [2x5 Ribbon Cables](https://www.sparkfun.com/products/8535)
* [2x3 Male Header](https://www.sparkfun.com/products/10877)
* [2x3 Ribbon Cable](https://www.digikey.com/en/products/detail/samtec-inc/IDSD-03-D-06-00-T/3476372)
* 1x 2N2222A
* 2x 4.7kOhm through hole resistors
* 1x 1N5817 through hole diode
* 1x 1kOhm through hole resistor
* 2x 0.1uF through hole axial capacitors

### Head Power Rail

Electrical schematics and datasheets found here: [head-power-rail](../../electrical-schematics/head-power-rail/REVISIONS.md)

* [12V Power Supply](https://www.digikey.com/en/products/detail/nte-electronics-inc/57-12D-10000-4/11651848)
* [Barrel jack](https://www.digikey.com/en/products/detail/globtek-inc/JACK-C-PC-10A-RA-R/8597889)
* [Toggle Switch](https://www.digikey.com/en/products/detail/e-switch/100SP1T2B4M6QE/378831) - to switch between fill mode/normal mode.
* 2x [5V Buck converter module](https://www.sparkfun.com/products/21256)
* 2x [3V3 Regulator](https://www.digikey.com/en/products/detail/stmicroelectronics/LD1117AV33/586006)
* 3x [2x5 Male Headers](https://www.sparkfun.com/products/8506)
* 3x [2x5 Ribbon Cables](https://www.sparkfun.com/products/8535)
* [2x3 Male Header](https://www.sparkfun.com/products/10877)
* [2x3 Ribbon Cable](https://www.digikey.com/en/products/detail/samtec-inc/IDSD-03-D-06-00-T/3476372)
* [Pump Control IC](https://www.digikey.com/en/products/detail/analog-devices-inc-maxim-integrated/MAX31760AEE-T/3976051) -
  unfortunately surface-mount. I couldn't source a through-hole part for this.
* [Header for Pump](https://www.digikey.com/en/products/detail/molex/0022053041/26693)
* [Button for Driving Pump Manually](https://www.digikey.com/en/products/detail/nkk-switches/BB15AH/1058979)
* [Raspberry Pi Pico](https://www.adafruit.com/product/5525)
* [CAN Module](https://modtronix.com/product/im1can/)
* [Water cooling block (copper)](https://www.amazon.com/Wendry-Suitable-Graphics-Diameter-Internal/dp/B07WH4VRW6/ref=sr_1_2?crid=3A4AK84O663QT&keywords=40mm+copper+water+block&qid=1680746922&sprefix=40mm+copper+water+block%2Caps%2C155&sr=8-2) - 40 x 40 x 10 mm
* [Water cooling block (aluminum)](https://www.amazon.com/dp/B07FTWWVDV/ref=sspa_dk_detail_2?psc=1&pf_rd_p=08ba9b95-1385-44b0-b652-c46acdff309c&pf_rd_r=92DHAX775TENDZK8526T&pd_rd_wg=22JSH&pd_rd_w=R9AwY&content-id=amzn1.sym.08ba9b95-1385-44b0-b652-c46acdff309c&pd_rd_r=e6e1ab6b-7cde-4f4d-83d5-191e2ff36299&s=pc&sp_csd=d2lkZ2V0TmFtZT1zcF9kZXRhaWxfdGhlbWF0aWM&spLa=ZW5jcnlwdGVkUXVhbGlmaWVyPUEzVlZLS0lJWFZMRkRYJmVuY3J5cHRlZElkPUEwMTQ2ODM2M1Q0MlJUV1ZFSkhMMSZlbmNyeXB0ZWRBZElkPUEwMzY0Mjg2M0UxOFk0SFMyWEQ0USZ3aWRnZXROYW1lPXNwX2RldGFpbF90aGVtYXRpYyZhY3Rpb249Y2xpY2tSZWRpcmVjdCZkb05vdExvZ0NsaWNrPXRydWU=) - 40 x 40 x 12 mm
* 2x [Shottky diodes that can handle at least 6A (Io)](https://www.digikey.com/en/products/detail/smc-diode-solutions/SB2060/5992790)
* 4x 10kOhm through hole resistor
* 2x 4.7kOhm through hole resistor
* 1x 1kOhm through hole resistor
* 1x 2N2222A
* 1x 1N5817 through hole diode
* TODO: Capacitors

### Head Sensor Board

Electrical schematics and datasheets found here: [head-sensor-board](../../electrical-schematics/head-sensor-board/REVISIONS.md)

* [Temperature/Pressure/Humidity Sensor](https://www.adafruit.com/product/2652)
* [6 DOF IMU](https://www.adafruit.com/product/4692)
* [Raspberry Pi Pico](https://www.adafruit.com/product/5525)
* 3x [2x3 Male Header](https://www.sparkfun.com/products/10877)
* 3x [2x3 Ribbon Cable](https://www.digikey.com/en/products/detail/samtec-inc/IDSD-03-D-06-00-T/3476372)
* 1x 2N2222A
* 1x 1N5817 through hole diode

### Neural Module - Eyes

Electrical schematics and datasheets found here: [neural-node-eyes](../../electrical-schematics/neural-node-eyes/REVISIONS.md)

* [Jetson Nano Devkit](https://www.nvidia.com/en-us/autonomous-machines/embedded-systems/jetson-nano/)
* [Micro SD Card](https://www.adafruit.com/product/2693)

### Eye Assembly (x2)

Electrical schematics and datasheets found here: [camera-carrier-board](../../electrical-schematics/camera-carrier-board/REVISIONS.md)

* [Cicuit Board](../../electrical-schematics/camera-carrier-board/REVISIONS.md)
* 2x [Raspberry Pi Camera Module (v2.x)](https://www.adafruit.com/product/3099) - one each eye
* 2x [Hobby Micro Servo with JST connectors](https://www.adafruit.com/product/4326) - one each eye

### Eyebrow Assembly

Electrical schematics and datasheets found here: [eyebrows](../../electrical-schematics/eyebrows/REVISIONS.md)

* 1x [Circuit board](../../electrical-schematics/eyebrows/REVISIONS.md) - See [procuring circuit boards](./building-artie-main.md#get-the-circuit-boards)
* 2x [1.14" Color LCD Display](https://www.waveshare.com/product/pico-lcd-1.14.htm)
* 2x [Raspberry Pi Pico](https://www.adafruit.com/product/5525)
* Ribbon Cable:
    * 1x [Female Header](https://www.sparkfun.com/products/8506)
    * 1x [Ribbon Cable](https://www.sparkfun.com/products/8535)
* 2x [JST Connectors](https://www.sparkfun.com/products/9750)
* 2x 2N2222A
* Resistors:
    * 5x 10kOhm through hole resistors
    * 2x 4.7kOhm through hole resistors
* Diodes:
    * 2x 1N5817 through hole diode

### Neural Module - Ears

Electrical schematics and datasheets found here: [neural-node-ears](../../electrical-schematics/neural-node-ears/REVISIONS.md)

* [Jetson Nano Devkit](https://www.nvidia.com/en-us/autonomous-machines/embedded-systems/jetson-nano/)
* [Micro SD Card](https://www.adafruit.com/product/2693)
* [Audio Board](https://www.waveshare.com/audio-card-for-jetson-nano.htm)

### Mouth Assembly

Electrical schematics and datasheets found here: [mouth](../../electrical-schematics/mouth/REVISIONS.md)

* [Speaker](https://www.adafruit.com/product/1314)
* [2" Color LCD Display](https://www.waveshare.com/pico-lcd-2.htm)
* [Raspberry Pi Pico](https://www.adafruit.com/product/5525)
* [2x5 Male Header](https://www.sparkfun.com/products/8506)
* 1x 2N2222A
* Resistors:
    * 1x 1kOhm through hole resistor
    * 2x 4.7kOhm through hole resistors
* Diodes:
    * 1x 1N5817 through hole diode

### Water Cooling System

TODO:

* A bunch of [compression connectors](https://www.amazon.com/BXQINLENX-Compression-Fitting-Computer-Straight/dp/B01DXSO5RY/ref=sr_1_9?crid=CR9UDR1RS6ML&keywords=compression+fittings+water+cooling&qid=1680737984&sprefix=compression+fittings+water+cooling%2Caps%2C206&sr=8-9)
* Soft tubing with inner-diameter (ID) of 8mm for some of it (connecting to RPi's water block)
* Soft tubing with inner-diameter (ID) of 10mm for most of it
* Distilled water (or if you want Artie to look cooler, you can opt for some fancy colored coolant, though it may void part warranties
  and may also reduce the lifespan of parts)
* [Pump/reservoir combo](https://www.amazon.com/Corsair-Hydro-Pump-Reservoir-Combo/dp/B08HSRD1WJ/ref=sr_1_2?crid=9GF4V5BCB6RM&keywords=corsair+xd5&qid=1680747279&sprefix=corsair+xd5%2Caps%2C202&sr=8-2) - Corsair XD5 RGB
* Radiators
* Flow meter

### Data Collection Module

TODO

### Motor Control Module

TODO

### Frame

TODO

* Lots of these [cheaper Dynamixel Servos](https://www.robotis.us/dynamixel-ax-12a/)
