# Status Command API

This document explains the JSON interface of the Artie Tool status command.

## Overview

When the `--json` flag is provided to any status subcommand, the output is formatted as a JSON object that can be parsed programmatically. This allows for easy integration with other tools and scripts.

## Common Structure

All JSON responses follow this general structure:

```json
{
  "command": "status",
  "module": "<module-name>",
  "timestamp": "<ISO-8601-timestamp>",
  "artie_name": "<artie-name>",
  "success": true|false,
  "error": "<error-message-if-any>",
  "data": {
    // Module-specific data
  }
}
```

### Common Fields

- **command**: Always "status"
- **module**: One of: "nodes", "pods", "mcus", "actuators", "sensors"
- **timestamp**: ISO 8601 formatted timestamp of when the command was executed
- **artie_name**: The name of the Artie being queried (null for pods or if not applicable)
- **success**: Boolean indicating if the command succeeded
- **error**: Error message if success is false, otherwise null
- **data**: Module-specific data structure (see below)

## Nodes Status

### List Nodes

Command: `artie-tool.py status nodes --list --json`

```json
{
  "command": "status",
  "module": "nodes",
  "timestamp": "2025-12-07T10:30:00Z",
  "artie_name": "Artie-001",
  "success": true,
  "error": null,
  "data": {
    "nodes": [
      {
        "name": "controller-node-Artie-001",
        "sbc_name": "controller-node"
      },
      {
        "name": "vision-node-Artie-001",
        "sbc_name": "vision-node"
      }
    ]
  }
}
```

### Node Status (Single)

Command: `artie-tool.py status nodes --node controller-node-Artie-001 --json`

```json
{
  "command": "status",
  "module": "nodes",
  "timestamp": "2025-12-07T10:30:00Z",
  "artie_name": "Artie-001",
  "success": true,
  "error": null,
  "data": {
    "nodes": [
      {
        "name": "controller-node-Artie-001",
        "status": "online",
        "role": "controller-node",
        "artie": "Artie-001",
        "labels": {
          "artie/artie-id": "Artie-001",
          "artie/node-role": "controller-node"
        }
      }
    ]
  }
}
```

### Node Status (All)

Command: `artie-tool.py status nodes --json`

```json
{
  "command": "status",
  "module": "nodes",
  "timestamp": "2025-12-07T10:30:00Z",
  "artie_name": "Artie-001",
  "success": true,
  "error": null,
  "data": {
    "nodes": [
      {
        "name": "controller-node-Artie-001",
        "status": "online",
        "role": "controller-node",
        "artie": "Artie-001",
        "labels": {
          "artie/artie-id": "Artie-001",
          "artie/node-role": "controller-node"
        }
      },
      {
        "name": "vision-node-Artie-001",
        "status": "offline",
        "role": "vision-node",
        "artie": "Artie-001",
        "labels": {}
      }
    ]
  }
}
```

## Pods Status

### List Pods

Command: `artie-tool.py status pods --list --json`

```json
{
  "command": "status",
  "module": "pods",
  "timestamp": "2025-12-07T10:30:00Z",
  "artie_name": null,
  "success": true,
  "error": null,
  "data": {
    "pods": [
      {
        "name": "artie-api-server-artie-001-5d7c8f9b-xz4k2"
      },
      {
        "name": "driver-mouth-artie-001-7f8d9c1a-abc12"
      }
    ]
  }
}
```

### Pod Status (Single)

Command: `artie-tool.py status pods --pod artie-api-server-artie-001-5d7c8f9b-xz4k2 --json`

```json
{
  "command": "status",
  "module": "pods",
  "timestamp": "2025-12-07T10:30:00Z",
  "artie_name": null,
  "success": true,
  "error": null,
  "data": {
    "pods": [
      {
        "name": "artie-api-server-artie-001-5d7c8f9b-xz4k2",
        "namespace": "artie",
        "status": "Running",
        "node": "controller-node-Artie-001",
        "containers": [
          {
            "name": "api-server",
            "ready": true,
            "restart_count": 0,
            "state": "running"
          }
        ]
      }
    ]
  }
}
```

### Pod Status (All)

Command: `artie-tool.py status pods --json`

Returns array of all pods with full status details (similar to single pod format).

## MCUs Status

### List MCUs

Command: `artie-tool.py status mcus --list --json`

```json
{
  "command": "status",
  "module": "mcus",
  "timestamp": "2025-12-07T10:30:00Z",
  "artie_name": "Artie-001",
  "success": true,
  "error": null,
  "data": {
    "mcus": [
      {
        "name": "eyebrow-left",
        "buses": ["can0", "lcd0"]
      },
      {
        "name": "eyebrow-right",
        "buses": ["can0", "lcd1"]
      }
    ]
  }
}
```

### MCU Status (Single)

Command: `artie-tool.py status mcus --mcu eyebrow-left --json`

```json
{
  "command": "status",
  "module": "mcus",
  "timestamp": "2025-12-07T10:30:00Z",
  "artie_name": "Artie-001",
  "success": true,
  "error": null,
  "data": {
    "mcus": [
      {
        "name": "eyebrow-left",
        "buses": ["can0", "lcd0"],
        "heartbeat": {
          "status": "not_implemented",
          "message": "Requires CAN bus integration"
        }
      }
    ]
  }
}
```

### MCU Status (All)

Command: `artie-tool.py status mcus --json`

Returns array of all MCUs with full status details (similar to single MCU format).

## Actuators Status

### List Actuators

Command: `artie-tool.py status actuators --list --json`

```json
{
  "command": "status",
  "module": "actuators",
  "timestamp": "2025-12-07T10:30:00Z",
  "artie_name": "Artie-001",
  "success": true,
  "error": null,
  "data": {
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
}
```

### Actuator Status (Single)

Command: `artie-tool.py status actuators --actuator eyebrow-left --json`

```json
{
  "command": "status",
  "module": "actuators",
  "timestamp": "2025-12-07T10:30:00Z",
  "artie_name": "Artie-001",
  "success": true,
  "error": null,
  "data": {
    "actuators": [
      {
        "name": "eyebrow-left",
        "type": "lcd",
        "bus": "lcd0",
        "status": {
          "status": "not_implemented",
          "message": "Requires CAN bus integration"
        }
      }
    ]
  }
}
```

### Actuator Status (All)

Command: `artie-tool.py status actuators --json`

Returns array of all actuators with full status details (similar to single actuator format).

## Sensors Status

### List Sensors

Command: `artie-tool.py status sensors --list --json`

```json
{
  "command": "status",
  "module": "sensors",
  "timestamp": "2025-12-07T10:30:00Z",
  "artie_name": "Artie-001",
  "success": true,
  "error": null,
  "data": {
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
    ]
  }
}
```

### Sensor Status (Single)

Command: `artie-tool.py status sensors --sensor eye-left --json`

```json
{
  "command": "status",
  "module": "sensors",
  "timestamp": "2025-12-07T10:30:00Z",
  "artie_name": "Artie-001",
  "success": true,
  "error": null,
  "data": {
    "sensors": [
      {
        "name": "eye-left",
        "type": "camera",
        "bus": "csi0",
        "status": {
          "status": "not_implemented",
          "message": "Requires sensor integration"
        }
      }
    ]
  }
}
```

### Sensor Status (All)

Command: `artie-tool.py status sensors --json`

Returns array of all sensors with full status details (similar to single sensor format).

## Error Responses

When an error occurs, the response will have `success: false` and include an error message:

```json
{
  "command": "status",
  "module": "nodes",
  "timestamp": "2025-12-07T10:30:00Z",
  "artie_name": null,
  "success": false,
  "error": "Cannot get Artie's HW configuration: No Artie found on the cluster.",
  "data": null
}
```

## Status Values

### Node Status
- `"online"`: Node is ready and operational
- `"offline"`: Node is not ready or not found

### Pod Status (Phase)
- `"Pending"`: Pod is waiting to be scheduled
- `"Running"`: Pod is running
- `"Succeeded"`: Pod has completed successfully
- `"Failed"`: Pod has failed
- `"Unknown"`: Pod status cannot be determined

### Container State
- `"running"`: Container is running
- `"waiting"`: Container is waiting to start
- `"terminated"`: Container has terminated
