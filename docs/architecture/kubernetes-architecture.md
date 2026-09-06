# Kubernetes Architecture

## Kubernetes Overview

Artie Framework leverages Kubernetes (K3S) as the orchestration layer for managing the upper-level software components
on a robot. Each single board computer (SBC) within the physical robot runs a K3S agent,
allowing it to participate in the Kubernetes cluster. A physically separate admin server functions as the Kubernetes master node,
orchestrating workloads across the cluster.

The general philosophy is that a robot's SBCs should be as lightweight as possible, focusing on running the necessary
Kubernetes agent and any essential services. All higher-level functionalities, such as experiment management,
data storage, and telemetry databases, are hosted on the admin server or additional off-robot compute nodes.
This design ensures that the robot's onboard resources are dedicated to real-time processing and control tasks,
while the admin server handles the overhead associated with managing the cluster and running non-real-time services.

TODO: Add a Kubernetes Architecture Diagram here.

The Kubernetes architecture consists of the following hardware components:

* **Admin Server (Kubernetes Master Node)**: This node runs the Kubernetes control plane components, including the K3S API server,
  scheduler, and controller manager. It is responsible for managing the cluster state, scheduling workloads, and
  coordinating communication between nodes.
* **Compute Nodes (Kubernetes Worker Nodes)**: Optional additional off-robot compute nodes can be added to the cluster to provide
  extra processing power for running workloads. These nodes run the K3S agent and can host various services and applications.
* **Single Board Computers (SBCs - Kubernetes Worker Nodes)**: Each SBC within the robot runs a K3S agent,
  allowing it to join the Kubernetes cluster as a worker node. The SBCs are primarily responsible for executing real-time control
  tasks and interfacing with hardware components through user-space driver containers deployed through Kubernetes.
* **Development Machine**: This is the machine used by developers to create and deploy experiments and workloads to the Artie cluster.
  It interacts with the Kubernetes API server on the admin server to manage resources and deploy applications. The development
  machine and the admin server can be the same physical machine if desired.

The Kubernetes architecture consists of the following software components (low-level):

* **K3S**: A lightweight Kubernetes distribution that is optimized for resource-constrained environments.
  K3S provides the core Kubernetes functionalities while minimizing resource usage, making it suitable for running on SBCs.
* **Kubernetes Control Plane**: The control plane components run on the admin server and manage the overall state of the cluster.
* **Kubernetes Worker Node Agents**: The SBCs and optional compute nodes run the K3S agent, allowing them to participate in the cluster
  and execute workloads.

The Kubernetes architecture consists of the following software components (high-level):

* **User-Space Driver Containers**: These containers run on the SBCs and provide interfaces to the robot's hardware components,
  such as sensors and actuators. They communicate with the microcontrollers over CAN bus and expose APIs for higher-level applications to interact with the hardware.
* **Experiment Management System**: This system runs on the admin server and provides tools for deploying and managing experiments on the robot.
  It interacts with the Kubernetes API to schedule workloads and monitor their execution.
* **Telemetry Database**: This component collects and stores telemetry data from the various nodes and services
  within the Artie cluster, enabling monitoring and analysis.
* **Data Storage Services**: These services provide persistent storage for experiment data, configurations, and other
  resources required by applications.
* **Application Workloads**: These are the various applications and services that provide the cognitive
  functionalities and capabilities of the robot. They are deployed as Kubernetes workloads and can be scaled across the
  cluster as needed.

The Kubernetes architecture consists of the following infrastructure components:

* **Networking**: Load balancing and service discovery mechanisms are implemented to facilitate
  communication between the various nodes and services within the Artie cluster.
* **Configuration Management**: Kubernetes ConfigMaps and Secrets are used to manage configuration data and sensitive information
  for the various components running on the cluster.
* **Taints and Tolerations**: These Kubernetes features are used to control the scheduling of workloads on specific nodes,
  ensuring that real-time control tasks are prioritized on the SBCs while non-real-time services are hosted on the admin server
  or compute nodes.

## Details

### Kubernetes Cluster Setup

The Kubernetes cluster is set up with the admin server as the master node and each SBC (and optional compute nodes) as worker nodes.

See the [Installation Guide](../architecture/kubernetes-architecture.md) for detailed steps on setting up the Kubernetes cluster.
In the reference robot, each SBC runs a Yocto image with a K3S agent pre-installed. In a custom-built robot, K3S will need
to be part of the SBC stack for any Rasbperry Pi, Orange Pi, Jetson, etc.
In order to join the cluster, each K3S agent needs to be configured
with the admin server's IP address and the cluster token, which can be done by using the Artie Workbench application
and selecting the "New Artie" option.

Note that the installation procedure will name the SBC nodes according to their role in the Artie hardware configuration file,
suffixed by the Artie name, such as `controller-node-myartie`, `perception-node-myartie`, etc. This is in contrast to most
of the other Kubernetes resources, which do not contain the Artie name in their resource names, as they are namespaced separately
for each Artie robot. This is a limitation of Kubernetes: nodes cannot be namespaced.

### Metadata Used in Artie Kubernetes Cluster

An Artie cluster's Kubernetes components utilize specific metadata labels and annotations to manage and identify resources within the cluster.

Note that all Artie-related Kubernetes resources are prefixed with `artie-` to distinguish them from other resources in the cluster,
and are lowercase, even if the Artie name or hardware type contains uppercase letters.

* **namespace**: Each robot operates with a different Kubernetes namespace, (defaulting to `artie`). This namespace encapsulates
  all Artie resources, ensuring isolation from other applications running in the cluster. Additionally, to distinguish between different
  *types* of robots (e.g., `artie00`, `roller-bot`), resources are labeled accordingly by means of a ConfigMap containing the hardware
  configuration for that specific robot type. To distinguish between different *instances* of Artie robots (e.g., multiple `artie00` robots),
  each instance is assigned a unique Artie ID (`artie/artie-id`), which is used in labels and annotations to identify resources belonging to
  that specific robot. Lastly, nodes are named according to their role and Artie ID (e.g., `controller-node-myartie`).
* **Labels**:
    * `app.kubernetes.io/name`: Always set to `artie`.
    * `app.kubernetes.io/managed-by`: `Helm` when managed by Helm, otherwise set to `artie-tooling`.
    * `app.kubernetes.io/instance`: The Helm release name, which is passed to Artie Tool as part of the deployment procedure,
      or derived from the task name if deploying a reference Chart, such as artie-base or artie-teleop.
      If deploying without Helm, such as through the installation tasks in
      Artie Tool, this label will be `artie-infrastructure`.
    * `app.kubernetes.io/version`: Found in the Helm chart's Chart.yaml file.
      If deployed through Artie Tool without Helm, this label is set to the Artie image tag used in the command.
    * `app.kubernetes.io/component`: The specific component or service within the cluster, such as `driver-eyebrows`.
    * `app.kubernetes.io/part-of`: Always set to `artie`.
    * `artie/artie-id`: The (lowercase) name of the robot. This label uniquely identifies the robot within the cluster.
      This label is applied to all resources associated with a specific robot instance, including nodes.
    * `artie/node-role`: This label is applied to nodes to indicate their role within the Artie architecture, such as `controller-node`,
      and should match the name found in the robot's hardware configuration file as well as each SBC's /etc/hosts file.
* **Taints**:
    * `artie/physical-bot-node`: A taint assigned to SBCs to prevent non-critical and non-compatible workloads from deploying to them.
    * `artie/controller-node`: The controller-node gets an additional taint to further discourage its use for non-critical
      workloads.
* **Container Environment Variables**:
    * `ARTIE_RUN_MODE`: Determines behavior of Artie components. Set to `production` for normal operation.
      Options are found in the enum `ArtieRunMode` in `kubespec.py` (reproduced here for convenience):
        - `production`: Normal operation mode.
        - `development`: Enables additional logging and debugging features.
        - `sanity`: Used for sanity testing.
        - `unit`: Used for unit testing.
        - `integration`: Used for integration testing.
    * `ARTIE_ID`: The name of the robot.
    * `ARTIE_GIT_TAG`: The Git tag or version of the Artie software being used.
    * `LOG_COLLECTOR_HOSTNAME`: The hostname of the log collector service, formatted as `<log-collector-hostname>-<artie-id>`.
    * `LOG_COLLECTOR_PORT`: The port number for the log collector service.
    * `METRICS_SERVER_PORT`: The port number for the metrics server.
* **Hardware Config Map**:
    * Each robot has a ConfigMap named `artie-hw-config` that contains
      the hardware configuration and capabilities of the robot.
* **Certificates**:
    * Each robot has a Kubernetes Secret named `artie-api-server-cert` that contains
      the API server certificate for secure communication between the robot and the admin server.
