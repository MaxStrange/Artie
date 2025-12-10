# Artie-Base Helm Chart

This chart contains the base Kubernetes configuration for all Artie robots.
It includes the minimum set of resources needed for any Artie instance to function.

## What's Included

### Deployments & Services

- **driver-reset**: Reset driver for microcontroller resets
- **driver-mouth**: Mouth actuator driver
- **driver-eyebrows**: Eyebrows actuator driver
- **artie-api-server**: Main API server for Artie control
- **telemetry-log-collector**: Centralized log collection service
- **telemetry-metrics-collector**: Metrics collection and monitoring

### Configuration

- **Priority Classes**: Separate priority levels for drivers and telemetry
- **Labels**: Standardized labels for all resources
- **Environment Variables**: Common environment configuration
- **Resource Management**: Default update strategies and restart policies

## Usage as a Library Chart

This chart is designed to be used as a dependency by specific Artie instance charts (like `artie00`):

```yaml
# In dependent chart's Chart.yaml
dependencies:
  - name: artie-base
    version: "0.1.0"
    repository: "file://../artie-base"
```

## Configurable Values

Key values that should be overridden by dependent charts:

- `artieId`: Unique identifier for the Artie instance (default: "artie-001")
- `imageTag`: Git tag/hash for container images (default: "3d23200b")
- `repository`: Docker registry for images (default: "maxfieldstrange")

See `values.yaml` for the complete list of configurable values.

## Templates

All templates are in the `templates/` directory:

- `driver-*.yaml`: Driver deployments and services
- `telemetry-*.yaml`: Telemetry deployments and services
- `*-priority-class.yaml`: Kubernetes priority classes
- `artie-api-server.yaml`: API server deployment and service

## Development

When making changes to artie-base:

1. Edit templates or values as needed
2. Increment the version in `Chart.yaml`
3. Update dependent charts to use the new version
4. Run `helm dependency update` in dependent charts
