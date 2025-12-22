# Firmware Contribution Guide

This document provides guidelines and best practices for contributing firmware to the Artie project.

## Overview of the Firmware

Artie firmware is responsible for interfacing with the robot's hardware components (mostly sensors and actuators).

### Where the Firmware Lives in the Ecosystem

TODO: Diagram showing where the firmware fits in the overall architecture.

### Design Philosophy of the Firmware

Firmware should strive for two main goals:

1. **Be super specific:** The firmware is responsible for interfacing with whatever actuators and sensors
   are attached to the MCU the firmware is running on, then exposing an API on the CAN bus for
   drivers to interact with. That's it. They are translators from higher-level drivers to the specific
   type of hardware that accomplishes what the driver is trying to do.
1. **Be decoupled:** Firmware should be written such that it is highly decoupled from the driver(s)
   it interacts with. We should be able to swap out a sensor for another sensor with only an update
   to the firmware - no update to the driver should be necessary.

The Artie ecosystem should ideally have many different isolated, decoupled hardware components
that can be swapped in/out based on the needs of a particular experiment.

## Building the Firmware
