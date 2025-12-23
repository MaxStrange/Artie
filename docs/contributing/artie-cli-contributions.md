# Artie CLI Contribution Guide

This document provides guidelines and best practices for
contributing code to Artie CLI.

## Overview of Artie CLI

Artie CLI is the typical programmatic mechanism for interfacing
with an Artie. It is not the usual way that an end user or even
a developer will interact with Artie; instead it is mostly
useful for test cases. See [the test section](./development-environment.md#artie-tool-test) of
the Development Environment Guide to see how Artie Tool
tests typically make use of Artie CLI.

Artie CLI is a Python application that is capable of exercising
the public APIs of each microservice directly (so long as it
is on the same network as the target microservice).

As Artie CLI is the main tool used for automated testing,
you should update it to include the ability to exercise
any new APIs you create. Currently that means adding
a new Python module to its 'modules' directory, but TODO: we should
consider having the modules live with their components,
and having Artie CLI determine which modules to import
based on the Artie HW config and some sort of broker
that can tell each microservice what other microservices
exist. Otherwise, as we add more and more modules, this program
is going to become pretty unwieldy.

### Design Philosophy of Artie CLI

Artie CLI is meant to be mostly used for very low-level
debugging (when you are really in the trenches) or
programatically for testing of various Artie components.

As such, please strive to adhere to the following principles:

1. **Minimalism:** Artie CLI's code is extremely terse.
   It just parses the arguments to determine what API to
   execute (and how), executes that API, then prints
   the result according to two specific library calls:
   `format_print_results()` and `format_print_status_results()`.
1. **Strict Adherence to Interface:** Artie CLI is used
   extensively in the automated testing, so its interface
   must be tightly controlled. Any APIs it exercises should
   be documented in the appropriate API doc. All results
   should try to print something through the two
   functions mentioned above.

Additionally, please note that Artie CLI has no notion of Kubernetes.
This is by design. It is meant to be run from within the cluster, and should
therefore not have any idea about Kubernetes, just like a driver application
has no notion of Kubernetes. Artie CLI exercises the public *microservice*
API of each component.
