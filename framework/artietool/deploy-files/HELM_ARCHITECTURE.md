# Helm Chart Sharing Architecture

## Overview

The Artie Helm charts now use a hierarchical structure where `artie-base` contains all common configuration
and specific Artie instances (like `artie00`) extend it through Helm's dependency mechanism.

## Structure

```
deploy-files/
├── artie-base/             # Base chart with common configuration
│   ├── Chart.yaml          # Chart metadata
│   ├── values.yaml         # Default values for all Arties
│   ├── templates/          # Kubernetes resource templates
│   │   ├── driver-*.yaml
│   │   ├── telemetry-*.yaml
│   │   └── artie-api-server.yaml
│   └── README.md
│
└── artie00/                # Specific Artie instance
    ├── Chart.yaml          # Declares artie-base as dependency
    ├── values.yaml         # Overrides for this instance
    ├── templates/          # Additional instance-specific templates
    │   └── NOTES.txt
    ├── .gitignore          # Ignores generated files
    └── README.md
```

## How It Works

### artie-base (Library Chart)

The `artie-base` chart is the foundation that contains:
- All common Kubernetes resources (drivers, telemetry, API server)
- Default configuration values
- Standard labels and environment variables
- Priority classes and update strategies

**Key files:**
- `values.yaml`: Provides defaults that can be overridden
- `templates/*.yaml`: Kubernetes manifests for all base resources

### artie00 (Instance Chart)

The `artie00` chart is a specific Artie robot instance that:
- Declares `artie-base` as a dependency in `Chart.yaml`
- Overrides values specific to this Artie in `values.yaml`
- Can add instance-specific resources in `templates/`

**Key files:**
- `Chart.yaml`: Contains dependency declaration
- `values.yaml`: Overrides passed to artie-base via the `artie-base:` key
- `templates/`: Optional instance-specific resources

## Deployment Process

### Automatic (Recommended)

The deployment system automatically handles dependencies:

```bash
python artie-tool.py deploy artie00
```

The `kube.py` module automatically runs `helm dependency update` before installation.

### Manual

If deploying with Helm directly:

```bash
# 1. Update dependencies
cd artietool/deploy-files/artie00
helm dependency update

# 2. Deploy the chart
helm install artie00-release . --namespace artie --create-namespace
```

## Creating New Artie Instances

To create a new Artie instance (e.g., `artie01`):

1. **Copy the artie00 structure:**
   ```bash
   cp -r artie00 artie01
   ```

2. **Update `Chart.yaml`:**
   ```yaml
   name: artie01
   description: Artie01 - A specific instance of an Artie robot based on artie-base
   # dependencies remain the same
   ```

3. **Update `values.yaml`:**
   ```yaml
   artie-base:
     artieId: artie01  # Change to unique ID
     # Add any artie01-specific overrides
   ```

4. **Update deployment configuration:**
   Add to `artietool/infrastructure/deploy_job.py`:
   ```python
   class DeploymentConfigurations(enum.StrEnum):
       # ...
       ARTIE01 = "artie01"
   ```

## Value Overrides

Values are passed to artie-base using the subchart prefix:

```yaml
# In artie00/values.yaml
artie-base:
  artieId: artie00
  imageTag: 3d23200b
  repository: maxfieldstrange

  # Override any base value
  ports:
    resetDriver: 18861

  # Add to base environment
  baseEnvironment:
    - name: ARTIE00_SPECIFIC_VAR
      value: "some-value"
```
