# API for Metrics Module

TODO: Determine the classes of things that get metrics associated with them and how to access them.
      When updating the metric in the code, make sure to access the appropriate metric by means of some schema,
      e.g., hw.can.reads
      Note that each metric also has 'attributes' set on it, which should
      include 'artie.id' and 'artie.service_name'.

HW:
    - System (polled by daemonsets with low-level access to HW):
        * Uptime
        * temperature
        * CPU usage
        * RAM usage
        * Disk space
        * Disk writes (wear usage for flash memory)
    - Buses:
        * CAN read/write latency/throughput
        * SPI read/write latency/throughput
        * GPIO read/write latency/throughput
        * etc.
    - Actuators:
        * Uptime
        * Number of commands issued
        * Command latency/throughput
    - Sensors:
        * Uptime
        * Number of readings taken
        * Reading latency/throughput

SW:
    - API:
        * Hits on a service's API function 1
        * Hits on a service's API function 2
        * Etc.

## HW

### System

#### Get System Uptime

Get a specific node's uptime.

TODO

#### Get System Temperature

Get a specific node's core temperature.

TODO

#### Get System CPU Usage

Get a specific node's CPU usage.

TODO

#### Get System RAM Usage

Get a specific node's RAM usage.

TODO

#### Get System Disk Space

Get a specific node's disk space usage.

TODO

#### Get System Disk Writes

Get a specific node's disk writes (wear usage for flash memory).

TODO

### Buses

#### Get CAN Bus Metrics

Get a specific node's CAN bus metrics or get an aggregated view across all nodes.

Also get CAN bus collisions.

TODO

#### Get SPI Bus Metrics

Get a specific node's SPI bus metrics or get an aggregated view across all nodes.

TODO

#### Get GPIO Bus Metrics

Get a specific node's GPIO bus metrics or get an aggregated view across all nodes.

TODO

### Actuators

#### Get Actuator Uptime

Get a specific actuator's uptime.

TODO

#### Get Actuator Command Counts

Get a histogram of commands issued to a specific actuator.

TODO

#### Get Actuator Command Latency/Throughput

Get a specific actuator's command latency/throughput.

TODO

### Sensors

#### Get Sensor Uptime

Get a specific sensor's uptime.

TODO

#### Get Sensor Reading Counts

Get a histogram of readings taken from a specific sensor.

TODO

#### Get Sensor Reading Latency/Throughput

Get a specific sensor's reading latency/throughput.

TODO

## SW

### API

#### Get API Function Hits

Get the number of hits on a specific service's API functions (by function name).

TODO
