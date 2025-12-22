# Release Process

This document describes the release process for Artie.

## Artie vs Artie Type vs Artie Release

The term "Artie" is highly overloaded, so it's important to clarify the distinctions:

* **Artie Type**: A specific configuration of hardware and software for an Artie robot.
  The Artie project oficially supports certain types, but other types are also possible (user-derived types).
  Currently, we support:
    - `artie00`: An Artie that is meant to simulate a newborn infant.
* **Artie Release**: A known, working combination of software, firmware, Yocto images, and bills of materials
  for each officially supported Artie Type. An Artie Release is identified by a suffix: "Artie Aardvark" for example.
  Each Artie Release is associated with a specific Git tag in this repository, and when all parts of that release
  are downloaded, procured, and built, the resulting robot should work as expected, as outlined by the documentation
  corresponding to that release.
* **Artie**: May refer to a specific physical robot or to the whole Artie project/ecosystem, depending on context.

## Releases

An Artie Release is always backward compatible with known Artie Types, and will include an updated bill of materials,
for each supported Artie Type, as well as updated software, firmware, and Yocto images for those Artie Types.

Hence, Artie Aardvark will provide all the necessary files to build an `artie00` robot, while Artie Baboon will provide
all the necessary files to build an `artie00` robot as well (with potentially updated parts, software, etc), but also
maybe an `artie01` robot if that type is supported in that release.

A release contains the following components:

1. **Bill of Materials (BOM)**: A list of all hardware components required to build each supported Artie Type.
   This includes links to purchase the parts, quantities, and any special instructions.
1. **Firmware**: The microcontroller firmware required for each supported Artie Type. These are typically bundled
   with the Yocto images or Docker images.
1. **Yocto Images**: The custom embedded Linux images required for each supported Artie Type.
1. **Docker Images**: Any Docker images required for each supported Artie Type.
1. **Helm Components**: The Helm charts and configuration files required to deploy the any software stack for each supported Artie Type.
   This includes a hierarchy of Helm charts, with a base chart (`artie-base`) and type-specific charts (e.g., `artie00`).
   It also includes a reference deployment configuration for deploying each supported Artie Type.
1. **Documentation**: Updated documentation for building, deploying, and using each supported Artie Type.

## Release Steps

1. **Prepare the Release Branch**:
    - Create a new branch from `main` named `release/<release-name>`.
    - Update the version numbers in relevant files:
        - TODO: Determine all the files that need version updates.
    - Update the bill of materials for each supported Artie Type.
    - Update the documentation to reflect any changes in the release.
    - Ensure all tests pass locally, *including hardware tests*, as these do not run in CI.
2. **Make a Pull Request**:
    - Push the `release/<release-name>` branch to the remote repository.
    - Create a pull request against `main`.
    - Ensure all tests pass in CI.
    - Get the pull request reviewed and approved by at least one other maintainer.
3. **Merge the Pull Request**:
    - Once approved, merge the pull request into `main`.
    - TODO: Run the release CI pipeline to build and package all release components.
    - Tag the merge commit with the release name (e.g., `Artie-Aardvark`).
