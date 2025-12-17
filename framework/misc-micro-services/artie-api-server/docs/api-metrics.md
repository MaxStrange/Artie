# API for Metrics Module

TODO: It may make sense to just pass through to Prometheus rather than have the API server handle metrics queries itself.
That way we can make use of Prometheus's visualization tools directly.

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
