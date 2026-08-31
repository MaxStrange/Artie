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

## Where the code lives

Artie is split across several repositories. Each owns its own source, its own task
definitions, its own version, and its contributor guide.

| Repository | Contains | Contributor guide |
|---|---|---|
| **Artie** (this one) | Documentation, architecture, the getting started guide | this file |
| [ArDK](https://github.com/ArtieBots/ArDK) | `libraries/` - `artie-util` (logging and common code), `artie-i2c`, `artie-gpio`, `artie-can` (CAN bus, C and Python), `artie-service-client` (service discovery, retries, timeouts for in-cluster applications), `artie-tooling` (shared by Artie Tool, Workbench and CLI)<br>`services/` - API server, pub/sub broker, service broker, telemetry<br>`base-image/`, `firmware/libraries/`, `deploy/artie-base/` | [library contributions](https://github.com/ArtieBots/ArDK/blob/main/docs/contributing/library-contributions.md) |
| [ArtieTool](https://github.com/ArtieBots/ArtieTool) | The build system, test harness and deployment tool | [Artie Tool contributions](https://github.com/ArtieBots/ArtieTool/blob/main/docs/contributing/artie-tool-contributions.md), [charts](https://github.com/ArtieBots/ArtieTool/blob/main/docs/contributing/chart-contributions.md), [release process](https://github.com/ArtieBots/ArtieTool/blob/main/docs/contributing/release-process.md) |
| [ArtieWorkbench](https://github.com/ArtieBots/ArtieWorkbench) | The graphical application | [Workbench contributions](https://github.com/ArtieBots/ArtieWorkbench/blob/main/docs/contributing/artie-workbench-contributions.md) |
| [ArtieCLI](https://github.com/ArtieBots/ArtieCLI) | The command line interface to a running Artie | [CLI contributions](https://github.com/ArtieBots/ArtieCLI/blob/main/docs/contributing/artie-cli-contributions.md) |
| [ArtieDaemons](https://github.com/ArtieBots/ArtieDaemons) | k3s host daemons for the admin and compute nodes | - |
| [Artie00](https://github.com/ArtieBots/Artie00) | One specific robot: hardware manifest, BOM, `firmware/`, `drivers/`, `electrical-schematics/`, `deploy/artie00/` | [firmware](https://github.com/ArtieBots/Artie00/blob/main/docs/contributing/firmware-contributions.md), [drivers](https://github.com/ArtieBots/Artie00/blob/main/docs/contributing/driver-contributions.md), [electronics](https://github.com/ArtieBots/Artie00/blob/main/docs/contributing/electronic-design.md), [mechanical](https://github.com/ArtieBots/Artie00/blob/main/docs/contributing/mechanical-design.md) |

The single board computers' Yocto images live in
[artie-controller-node](https://github.com/MaxStrange/artie-controller-node), which Artie
Tool clones when building them.

Artie Tool builds across all of these at once. `artie-tool workspace sync` fetches them,
and `artie-tool workspace status` shows where each one currently resolves to. See
[setting up a development environment](./docs/contributing/development-environment.md).

## Contribution Guide

Please read the following documents for more information on contributing:

1. [Release process](https://github.com/ArtieBots/ArtieTool/blob/main/docs/contributing/release-process.md)
1. [Versioning and releases](./docs/contributing/versioning.md)
1. [Pull request process](./docs/contributing/pull-request-process.md)
1. [Overall architecture](./docs/contributing/overall-architecture.md)
1. [Setting up a development environment](./docs/contributing/development-environment.md)
1. [Electronic design contributions](https://github.com/ArtieBots/Artie00/blob/main/docs/contributing/electronic-design.md)
1. [Mechanical design contributions](https://github.com/ArtieBots/Artie00/blob/main/docs/contributing/mechanical-design.md)
1. [Firmware contributions](https://github.com/ArtieBots/Artie00/blob/main/docs/contributing/firmware-contributions.md)
1. [Yocto image contributions](./docs/contributing/yocto-image-contributions.md)
1. [Driver contributions](https://github.com/ArtieBots/Artie00/blob/main/docs/contributing/driver-contributions.md)
1. [Library contributions](https://github.com/ArtieBots/ArDK/blob/main/docs/contributing/library-contributions.md)
1. [Artie CLI contributions](https://github.com/ArtieBots/ArtieCLI/blob/main/docs/contributing/artie-cli-contributions.md)
1. [Artie Tool contributions](https://github.com/ArtieBots/ArtieTool/blob/main/docs/contributing/artie-tool-contributions.md)
1. [Artie Workbench contributions](https://github.com/ArtieBots/ArtieWorkbench/blob/main/docs/contributing/artie-workbench-contributions.md)
1. [Chart contributions](https://github.com/ArtieBots/ArtieTool/blob/main/docs/contributing/chart-contributions.md)
1. [Simulator contributions](./docs/contributing/simulator-contributions.md)
