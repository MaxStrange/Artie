# Helm Chart Architecture

## Overview

Artie is deployed as two independent Helm releases, installed alongside each other:

- **`artie-base`** — the platform services every Artie needs, shipped with ArDK.
- **a robot chart** such as **`artie00`** — the workloads specific to one robot's
  hardware, shipped with that robot.

They are deliberately *not* a chart and subchart. Each is owned by a different component
and, once the repositories are split, lives in a different repository; making one depend
on the other would mean a cross-repository chart reference and would stop either being
independently ownable. Artie Tool installs both and keeps the values they share
consistent.

## Structure

Each component ships the chart that deploys it, in its own `deploy/` directory:

```
framework/ardk/deploy/
└── artie-base/                     # Platform services - ArDK owns this
    ├── Chart.yaml
    ├── values.yaml
    ├── templates/
    │   ├── artie-api-server.yaml
    │   ├── artie-rpc-broker.yaml
    │   ├── broker-pvc.yaml
    │   ├── default-network-policy.yaml
    │   ├── driver-priority-class.yaml
    │   └── telemetry-*.yaml
    └── README.md

artie00/deploy/
└── artie00/                        # One robot's hardware - Artie00 owns this
    ├── Chart.yaml
    ├── values.yaml
    └── templates/
        ├── driver-eyebrows.yaml
        ├── driver-mouth.yaml
        └── NOTES.txt
```

## How it works

### artie-base

The platform every robot runs on:

- the API server, the RPC broker and its cache volume
- telemetry log and metrics collectors
- the default network policy
- the `driver-priority-level` PriorityClass

That PriorityClass lives here rather than in a robot chart on purpose: a PriorityClass is
cluster-scoped, so several robot charts on one cluster have to share a single object
instead of each trying to create its own and colliding.

`artie-base` contains no hardware drivers. It has no idea what an eyebrow is.

### artie00

One specific robot. It holds the DaemonSets and Services for that robot's hardware
drivers — today the mouth and the eyebrows.

## The shared contract

Because the two charts are separate releases, neither can read the other's values.
The settings they must agree on are duplicated in both `values.yaml` files, under a
"platform contract" heading in the robot chart:

`namespace`, `labels`, `constantKeys`, `ports`, `baseEnvironment`, `controllerNodeName`,
`driverPriorityClass`, and the shared identity values `artieId`, `imageTag`, `repository`.

These are the wire contract between a robot's drivers and the platform services they talk
to, and they are also mirrored in `artie_tooling/kubespec.py` and
`artie_util/constants.py`. **If you change one, change all of them.**

Artie Tool keeps the three values a deployment actually varies — `artieId`, `imageTag`
and `repository` — consistent across both releases by passing them with `--set` at
install time, so those three do not have to be edited in the files.

## Deploying

```bash
artie-tool deploy base       # platform services (artie-base)
artie-tool deploy artie      # the robot (artie00)
```

Or with Helm directly:

```bash
helm install artie-base framework/ardk/deploy/artie-base --namespace artie --create-namespace
helm install artie00    artie00/deploy/artie00          --namespace artie
```

Note that installing the robot chart alone gives you drivers with no platform to talk to.
Install `artie-base` first.

## Adding a new robot

1. Copy the chart:
   ```bash
   cp -r artie00/deploy/artie00 artie01/deploy/artie01
   ```
2. Update `Chart.yaml` — set `name: artie01` and the description.
3. Update `values.yaml` — set `artieId: artie01`, and adjust the driver workloads in
   `templates/` to match that robot's hardware. Keep the platform contract values
   identical to `artie-base`'s.
4. Add a deploy task at `artie01/.artie/tasks/deploy-tasks/artie01.yaml`, pointing
   `chart:` at `deploy/artie01`. Chart paths are relative to the component that owns the
   task.
5. Add the configuration name to `DeploymentConfigurations` in
   `artietool/infrastructure/deploy_job.py`.
