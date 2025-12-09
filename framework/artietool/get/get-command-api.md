# Get Command API

This document explains the JSON and YAML interfaces of the Artie Tool get command.

## Overview

The `get` command retrieves configuration and metadata from the Artie cluster. When the `--json` or `--yaml` flags are provided, the output is formatted accordingly for programmatic consumption.

## Command Structure

```bash
artie-tool.py get <module> [--json | --yaml]
```

### Available Modules

- **hw-config**: Retrieve the hardware configuration for the deployed Artie

### Output Format Flags

- `--json`: Format output as JSON
- `--yaml`: Format output as YAML
- Neither flag: Human-readable text output

## Hardware Configuration

The `hw-config` module retrieves the complete hardware configuration for the Artie instance deployed in the Kubernetes cluster.

### Command

```bash
artie-tool.py get hw-config [--json | --yaml]
```

### JSON Output

Command: `artie-tool.py get hw-config --json`

```json
{
  "artie_type_name": "artie00",
  "sbcs": [
    {
      "name": "controller-node",
      "architecture": "linux/arm64",
      "buses": [
        "can0",
        "power-input0",
        "uart0"
      ]
    },
    {
      "name": "vision-node",
      "architecture": "linux/arm64",
      "buses": [
        "can0",
        "csi0",
        "csi1"
      ]
    },
    {
      "name": "ear-node",
      "architecture": "linux/arm64",
      "buses": [
        "can0"
      ]
    },
    {
      "name": "muscle-node",
      "architecture": "linux/arm64",
      "buses": [
        "can0",
        "power-input1"
      ]
    }
  ],
  "mcus": [
    {
      "name": "eyebrow-left",
      "buses": [
        "can0",
        "lcd0"
      ]
    },
    {
      "name": "eyebrow-right",
      "buses": [
        "can0",
        "lcd1"
      ]
    }
  ],
  "sensors": [
    {
      "name": "eye-left",
      "type": "camera",
      "bus": "csi0"
    },
    {
      "name": "eye-right",
      "type": "camera",
      "bus": "csi1"
    }
  ],
  "actuators": [
    {
      "name": "eyebrow-left",
      "type": "lcd",
      "bus": "lcd0"
    },
    {
      "name": "eyebrow-right",
      "type": "lcd",
      "bus": "lcd1"
    }
  ]
}
```

### YAML Output

Command: `artie-tool.py get hw-config --yaml`

```yaml
artie_type_name: artie00
actuators:
- bus: lcd0
  name: eyebrow-left
  type: lcd
- bus: lcd1
  name: eyebrow-right
  type: lcd
mcus:
- buses:
  - can0
  - lcd0
  name: eyebrow-left
- buses:
  - can0
  - lcd1
  name: eyebrow-right
sbcs:
- architecture: linux/arm64
  buses:
  - can0
  - power-input0
  - uart0
  name: controller-node
- architecture: linux/arm64
  buses:
  - can0
  - csi0
  - csi1
  name: vision-node
- architecture: linux/arm64
  buses:
  - can0
  name: ear-node
- architecture: linux/arm64
  buses:
  - can0
  - power-input1
  name: muscle-node
sensors:
- bus: csi0
  name: eye-left
  type: camera
- bus: csi1
  name: eye-right
  type: camera
```

### Human-Readable Output

Command: `artie-tool.py get hw-config`

```
HW Configuration for Artie-001:
HWConfig(artie_type_name='artie00', sbcs=[SBC(name='controller-node', architecture='linux/arm64', buses=['can0', 'power-input0', 'uart0']), SBC(name='vision-node', architecture='linux/arm64', buses=['can0', 'csi0', 'csi1']), SBC(name='ear-node', architecture='linux/arm64', buses=['can0']), SBC(name='muscle-node', architecture='linux/arm64', buses=['can0', 'power-input1'])], mcus=[MCU(name='eyebrow-left', buses=['can0', 'lcd0']), MCU(name='eyebrow-right', buses=['can0', 'lcd1'])], sensors=[Sensor(name='eye-left', type='camera', bus='csi0'), Sensor(name='eye-right', type='camera', bus='csi1')], actuators=[Actuator(name='eyebrow-left', type='lcd', bus='lcd0'), Actuator(name='eyebrow-right', type='lcd', bus='lcd1')])
```

## Data Structure Reference

### HWConfig

Top-level hardware configuration object.

| Field | Type | Description |
|-------|------|-------------|
| `artie_type_name` | string | The type/model of Artie (e.g., "artie00") |
| `sbcs` | array[SBC] | List of Single Board Computers in this Artie |
| `mcus` | array[MCU] | List of Microcontroller Units in this Artie |
| `sensors` | array[Sensor] | List of sensors in this Artie |
| `actuators` | array[Actuator] | List of actuators in this Artie |

### SBC (Single Board Computer)

Represents a compute node in the Artie cluster.

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Unique identifier for the SBC (e.g., "controller-node") |
| `architecture` | string | Platform architecture (e.g., "linux/arm64") |
| `buses` | array[string] | List of bus IDs this SBC can access (e.g., "can0", "csi0") |

### MCU (Microcontroller Unit)

Represents a microcontroller in the Artie system.

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Unique identifier for the MCU (e.g., "eyebrow-left") |
| `buses` | array[string] | List of bus IDs this MCU can access (e.g., "can0", "lcd0") |

### Sensor

Represents a sensor device.

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Unique identifier for the sensor (e.g., "eye-left") |
| `type` | string | Type of sensor (e.g., "camera", "imu", "microphone") |
| `bus` | string | Bus ID this sensor is connected to (e.g., "csi0", "i2c1") |

### Actuator

Represents an actuator/output device.

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Unique identifier for the actuator (e.g., "eyebrow-left") |
| `type` | string | Type of actuator (e.g., "lcd", "motor", "servo") |
| `bus` | string | Bus ID this actuator is connected to (e.g., "lcd0", "can0") |

## Bus ID Reference

Common bus identifiers used in Artie configurations:

| Bus ID | Description |
|--------|-------------|
| `can0`, `can1` | CAN bus interfaces for inter-component communication |
| `csi0`, `csi1` | Camera Serial Interface ports for camera sensors |
| `i2c0`, `i2c1` | I²C bus interfaces for sensors and peripherals |
| `lcd0`, `lcd1` | LCD display interfaces |
| `uart0`, `uart1` | Serial UART interfaces |
| `usb0`, `usb1` | USB interfaces |
| `power-input0`, `power-input1` | Power input monitoring interfaces |

## Error Handling

If the hardware configuration cannot be retrieved (e.g., no Artie deployed, cluster unreachable), the command will:

1. Print an error message to stderr
2. Exit with a non-zero return code
3. Not produce JSON/YAML output

Example error:
```
ERROR: Cannot get Artie's HW configuration: Cannot find any deployed Arties.
```

## API Version

The hardware configuration format follows the `api-version: v1` specification. Future versions may introduce additional fields or modify the structure while maintaining backward compatibility where possible.

## Related Commands

- `artie-tool.py status nodes --json`: Get runtime status of SBCs/K3S nodes
- `artie-tool.py status mcus --json`: Get runtime status of MCUs
- `artie-tool.py status sensors --json`: Get runtime status of sensors
- `artie-tool.py status actuators --json`: Get runtime status of actuators

The `get hw-config` command returns the static hardware configuration, while the `status` commands return dynamic runtime status information.
