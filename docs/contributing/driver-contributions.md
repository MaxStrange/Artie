# Driver Contribution Guide

This document provides guidelines and best practices for contributing drivers to the Artie project.

## Overview of Drivers

The term "drivers" in the Artie ecosystem typically refers to user-space
drivers, which are applications running in Docker containers
that have been deployed to SBCs via Kubernetes daemonsets.
These user-space drivers are responsible for placing hardware
(which is typically present via MCUs on the CAN bus) onto the microservices
plane. As such, they operate as a translation layer from the upper layers
of the Artie stack to the hardware layers.

The microservices plane of the Artie stack operates by means of
HTTP, RPC, and pub/sub, so driver applications should typically provide
an API that is over one ore more of those protocols.

### Where the Drivers Live in the Ecosystem

TODO: Diagram showing where the drivers fit in the overall architecture.

### Design Philosophy of the Drivers

Drivers should provide a service, and should generally be the one
point of control (at the microservices level) over a particular feature
of an Artie.

For example, a single driver might be responsible for eyebrow control
of both eyebrows. How abstracted this eyebrow driver's API is
depends on the purpose of the robot. If the purpose of the Artie in question
is to study motor control of articulator muscles, then this driver
might have a very high level API, such as "happy", "sad", etc. On the other
hand, if the Artie's purpose is to study motor control of facial expressions,
a much lower-level API may be a better fit for that workload, such as
"contract_frontalis_muscle".

Since the exact workload of a particular Artie is not known ahead of time,
the Artie project will add many drivers over time, with
the operator selecting from among them using Helm charts.
As such, it is important to make sure each driver has a solid set of
automated tests to ensure no supported driver breaks as the other parts of Artie change.

TODO:

* Drivers should have a set of supported hardware. They expect
  to find at least some subset of that hardware attached to
  whichever bus they interact with (typically CAN).
  They should have labels that specify what they are capable of,
  e.g., eyebrow-driver-01 might have a 'compatible' field that
  specifies interfaces it is compatible with, such as 'motorv1'.
  These interfaces are also labeled in the Artie HW Config file,
  like: eyebrow-mcu-left: compatible: motorv1, which tells the
  release task that only Helm charts that provide a driver
  that speaks motorv1 and a left eyebrow firmware that speaks
  motorv1 can be deployed to this Artie.
* As part of Artie Tool deployment, compatibilities should be checked
  and warnings/errors reported: warnings are things like you are
  attempting to deploy a Chart that has no driver for some
  hardware - that hardware will be unavailable, while errors are
  things like you are attempting to deploy a Chart that has
  two drivers that are trying to own the same component or
  there is a driver that does not speak any protocol that anything
  on its bus can speak.

## Building a Driver

To build a driver, use Artie Tool like this:

`python artie-tool.py build <target> -e --docker-repo <target-repo> --docker-logs [--insecure] -o artie-tool-log.txt`

This will run Artie Tool's build command over the given target task.

## Source Code

Driver source code lives in Artie Common (`artie-common/drivers`),
unless it is source code for a driver that can only make sense
in one particular type of Artie (which would be unusual), in which
case it lives in that Artie's directory.

Drivers are microservices and can therefore be written in any language
so long as they are available on their buses, however they are typically
written in Python and make use of some of the libraries found
in `framework/libraries/`.
