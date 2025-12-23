# Library Contribution Guide

This document provides guidelines and best practices for contributing
library code to the Artie Project.

## Overview of the Libraries

Libraries are software libraries that might be used by more than one Artie
component. They come in a few flavors:

* Firmware Libraries: These live in `artie-common/firmware/libraries` and are libraries for use in the firmware.
* Artie Component Libraries: These live in `framework/libraries/`
  (TODO: they should really live in Artie Common) and
  are used by more than one Artie component application,
  such as drivers.
* Artie Infrastructure Libraries: These live in `framework/libraries/` and are used
  by more than one Artie infrastructure component, such
  as Artie Tool and Artie Workbench.

## Building the Libraries

Building application libraries (as opposed to firmware libraries)
is typically done inside the Artie Base Image, which is
a Docker image [found here](../../framework/libraries/base-image/Dockerfile).
The base image is pulled into the other build tasks by means
of their Dockerfiles as needed.

So if you add a new library, you will likely add it to the
Artie Base Image and then rebuild your target with Artie Tool,
which will detect the change and rebuild the dependency chain.
