# Yocto Image Contribution Guide

This document provides guidelines and best practices for contributing (to) Yocto images (to) the Artie project.

## Overview of Yocto Images

Yocto images are custom Linux distributions built using the Yocto Project. They are tailored to run on Artie robots,
providing only the bare-minimum OS-level functionality required for Artie to operate effectively, thereby
minimizing resource usage and maximizing performance by ensuring the CPU and memory are dedicated to Artie's applications
instead of unnecessary OS services.

The Yocto Images are found in different GitHub repositories, depending on the target SBC architecture:

* [artie-controller-node](https://github.com/MaxStrange/artie-controller-node): Yocto image for the controller node SBC (rPi 4b).

### Where the Yocto Images Live in the Ecosystem

The Yocto images run on the single board computers (SBCs) that are part of Artie. They provide the operating system
environment for the Artie drivers and other software components that run on the SBCs.
Effectively, they are just lightweight Linux distributions customized to only include the necessary
pieces to get K3S up and running (and to allow hardware communication with any attached devices, especially
the CAN bus).

### Design Philosophy of the Yocto Images

Yocto images should strive for the following main goals:

1. **Minimalism:** The Yocto images should include only the essential packages and services required for Artie to function.
1. **Long term support:** The Yocto images should be based on stable releases of the Yocto Project to ensure long-term support
   because it is super annoying to update a Yocto image to a new version of Yocto.

## Building the Yocto Images

To get started with Yocto development, please ensure you meet the
[Yocto Project hardware requirements](https://docs.yoctoproject.org/5.0.14/ref-manual/system-requirements.html),
in particular, note that you must use Linux (and our tooling assumes Ubuntu), and the more hard drive
space, RAM, and CPU speed you have, the better. Building Linux is not a fast process, but the Yocto
build system (Bitbake) does a very good job at speeding it up, but only by consuming as many resources
as it possibly can.

Next, ensure you install all the required software packages:

`sudo apt install build-essential chrpath cpio debianutils diffstat file gawk gcc git iputils-ping libacl1 liblz4-tool locales python3 python3-git python3-jinja2 python3-pexpect python3-pip python3-subunit socat texinfo unzip wget xz-utils zstd`

Finally, you can run Artie Tool:

`python artie-tool.py build yocto-controller-module -e --yocto-image artie-image-dev --repos-directoy <path to where you will put the artie-controller-node repo>`

If something goes wrong with building and you need to rerun, make sure to add the `--skip-clone` arg. Otherwise
it will error out, as it won't want to re-download the git repo.

TODO: A general Yocto tutorial
