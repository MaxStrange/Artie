# Stuff Left To Do

## Eyebrows

* Modify FW for left vs right eye
* Bring up PCB
    * Document BOM
* Replace Arduino with RPi Controller Module
* Test Servo
* Create 3D printable faceplate
* Create eyeball enclosure
* 3D print enclosures and faceplate
* Figure out limit switches
* Get FW programming working from Controller Module

## Mouth

* Determine how much FW is common between mouth and eyebrows
* Source sensors for mouth PCB
    * Temperature?
    * 6 DOF IMU over SPI (both I2Cs are in use)
* Test in breadboard
* Create PCB
* Bring up PCB
    * Document BOM

## Controller Module

* Yocto:
    * systemd
    * I2C
    * UART
    * Include the eyebrow and mouth FW binaries into image
* Drivers:
    * Start with user-space I2C driver using sysfs
    * Create kernel module device driver that attaches to I2C bus
    * Driver should program FW into the devices
* Application:
    * CLI for debugging/testing the whole system
    * Flask app that accepts REST API and forwards into I2C
    * k3s
    * Get Flask app running on k3s
    * Replace Flask with whatever micro service framework and DAPR + Kafka?
* PCB:
    * Schematic
    * Route
* Enclosure:
    * Create 3D printable enclosure
    * 3D print it

## Neural Module: Ears

* Yocto
* Drivers
* Application
* PCB
* Enclosure:
    * Need an interface to ears, which have the mics in them.

## Neural Module: Eyes

* Yocto
* Drivers
* Application
* PCB
* Enclosure
