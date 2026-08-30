# Contributing

Thank you for your interest in contributing to the Artie project!
We welcome contributions to help improve and expand the capabilities of Artie,
so long as they align with the project's vision (or especially if they fix bugs :D)

## Vision

So what is the vision? Artie aims to be a fully open source, 3D-printable robot that is as affordable as possible,
while still being easy to use and extend. Artie's main purpose is for data collection and testing developmental robotics theories,
but a side effect of this is that Artie can also be used for education and hobbyist robotics.

The so-called "north star" of Artie is that it would ultimately be indistinguishable from a human infant in terms
of its learning and development. There is obviously a long way to go before we reach that point, but every contribution
that helps us get closer to that goal is welcome!

To that end, we have compiled a list of requirements for Artie.
TODO: Link to the list of requirements when it is ready.

The requirements document is unlike your typical engineering requirements document. It consists of a list of
developmental biology and psychology research results that provide a snapshot at different timepoints in human development
with links to the original research papers. If Artie replicates these results, he meets the requirements of being human.

Of course, we also have more traditional software and hardware requirements for Artie, which are documented TODO.

## Overall Design Considerations

When contributing to Artie, please keep the following design considerations in mind (these are mostly
just good software engineering principles):

- **Affordability**: Strive to keep costs low to make Artie accessible to a wider audience.
- **Modularity**: Design components to be easily replaceable and upgradable. Each layer of Artie's architecture
  should know as little about the layers above and below it as possible. That is, interfaces should be well-defined and
  decoupled. It is hard to know ahead of time what capabilities a future Artie might need, so modularity is key.
- **Extensibility**: Ensure that new features and functionalities can be added without major overhauls to the existing system.
- **Usability**: Prioritize ease of use for both developers and end-users. Clear documentation is important.
- **Open Source**: The licensing model for Artie is MIT for software, except for Workbench, which requires LGPLv3 due to
  its use of Qt. Any contributions must be compatible with these licenses. Hardware is licensed under CERN-OHL-P. Yocto
  images are licensed as Linux images, with all kinds of licenses for different components,
  see the [Yocto documentation](https://docs.yoctoproject.org/next/overview-manual/development-environment.html#licensing) for details.

**Important concepts:**

* All Artie software components, especially infrastructure and tooling, are designed to support
  multiple Artie robot *instances* of potentially different *types* running in parallel.
  For example, the Artie Tool and Artie Workbench should be able to
  manage multiple Arties (which may not have the same hardware or software configurations) at once
  (typically by allowing the user to switch between them or choose which one to interact with).
* The Artie ecosystem is composed of multiple layers, each with its own responsibilities and interfaces.
  This guide will discuss each of these layers in detail.
  These layers include (from bottom to top):
  - Hardware: circuit boards (PCBs), single board computers (SBCs or 'nodes'), microcontrollers (MCUs),
    sensors, actuators (which is a term we use for any output device - so displays are also 'actuators'),
    and the physical 3D-printed structure of the robot.
  - Firmware: MCU firmware
  - Yocto Images: custom embedded Linux images
  - Libraries: shared libraries between software components
  - Drivers: applications that run on the SBCs and interface with hardware
  - Artie CLI: command-line interface for controlling a physical Artie
  - Artie Tool: tool for flashing, testing, building, releasing, etc.
  - Artie Workbench: desktop graphical user interface for controlling and configuring Arties
  - Charts: Helm charts for deploying Artie software
  - Simulator: simulated environment and simulated Artie for training and testing

## File Structure

The repository is organized into the following main directories:

**Meta Directories**

These directories contain meta-information about the project.

* `.circleci/`: CircleCI configuration files for automated testing and building.
* `build-artifacts/`: Artifacts generated during the build process.
* `docs/`: Documentation.

**Infrastructure and Common Software Component Directories**

These directories contain infrastructure-related code and configurations.

* `framework/`: Core framework code for Artie.
    * `ardk/`: Artie Development Kit (ArDK) code and related resources.
        * `base-image/`: Docker images used in building various Artie components.
        * `firmware/`: Bootloader and libraries that can be used by various Artie MCUs.
        * `libraries/`: Common libraries used by more than one element of Artie.
            * `artie-can/`: Application-level (SBC) library and FW library for interacting with the CAN bus.
            * `artie-gpio/`: Application-level (SBC) library for interacting with GPIO pins.
            * `artie-i2c/`: Application-level (SBC) library for interfacing with the I2C bus.
            * `artie-service-client/`: All applications running in Docker containers inside the K3S cluster
              should include this library. It provides means to discover other services, handle retries,
              and handle timeouts when calling other microservices.
            * `artie-tooling/`: Library common to tooling components, such as Artie Tool, Artie Workbench,
              and Artie CLI. Note the distinction between this library and `artie-util`, which is for
              actual Artie software, not for Artie tools.
            * `artie-util/`: Non-specific software common to Artie application components, such as logging.
        * `services/`: Microservices that are expected to be found in all Artie deployments.
            * `artie-api-server/`: Code and Dockerfile for Artie API server, which currently serves as the single input/output
              gateway for the Artie Kubernetes cluster.
            * `artie-pubsub-broker/`: Code and Dockerfile for the Pub/Sub messaging broker.
            * `artie-service-broker/`: Code and Dockerfile for the service broker.
            * `telemetry/`: Code and Dockerfiles for the telemetry microservices.
    * `artietool/`: Artie Tool code and related resources.
      See the [Artie Tool contributing guide](./docs/contributing/artie-tool-contributions.md) for more information.
    * `cli/`: Artie CLI code and related resources.
      See the [Artie CLI contributing guide](./docs/contributing/artie-cli-contributions.md) for more information.
    * `daemons/`: Daemons that run as part of the Kubernetes cluster, but do not run on Artie SBCs.
    * `workbench/`: Code for Artie Workbench.

**Artie Proper**

These directories contain items corresponding to actual Artie bots.

* `artie00/`: Contains items that are specific to only Artie00, an Artie type that simulates a newborn infant.

## Contribution Guide

Please read the following documents for more information on contributing:

1. [Release process](./docs/contributing/release-process.md)
1. [Versioning and releases](./docs/contributing/versioning.md)
1. [Pull request process](./docs/contributing/pull-request-process.md)
1. [Overall architecture](./docs/contributing/overall-architecture.md)
1. [Setting up a development environment](./docs/contributing/development-environment.md)
1. [Electronic design contributions](./docs/contributing/electronic-design.md)
1. [Mechanical design contributions](./docs/contributing/mechanical-design.md)
1. [Firmware contributions](./docs/contributing/firmware-contributions.md)
1. [Yocto image contributions](./docs/contributing/yocto-image-contributions.md)
1. [Driver contributions](./docs/contributing/driver-contributions.md)
1. [Library contributions](./docs/contributing/library-contributions.md)
1. [Artie CLI contributions](./docs/contributing/artie-cli-contributions.md)
1. [Artie Tool contributions](./docs/contributing/artie-tool-contributions.md)
1. [Artie Workbench contributions](./docs/contributing/artie-workbench-contributions.md)
1. [Chart contributions](./docs/contributing/chart-contributions.md)
1. [Simulator contributions](./docs/contributing/simulator-contributions.md)
