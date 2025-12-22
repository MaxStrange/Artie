# Setting up a Development Environment

This document provides instructions for setting up a development environment for contributing to the Artie project.
These instructions closely mirror those used by an end-user to set up and administer an Artie, but with
a few additional steps that are useful for development.

Hence, first follow the instructions in the [Artie Out of the Box (Edge Deployment)](../out-of-the-box/edge.md) guide.

Once you have followed those instructions and have a working Artie deployment, you can set up your development
environment by following these additional steps.

## Set Up a Local Docker Registry

If you develop software for Artie, you will need to build Docker images and push them to a Docker registry
with astounding size and frequency. Using something like DockerHub is not typically feasible for fast iteration,
as you will hit rate limiting unless you are paying for a plan.

TODO: Describe setting this up, including super obnoxious errors involving insecure registries.

## Working with Artie Tool

Once the local Docker registry is set up, you can build all the images and firmware with Artie Tool:

`python artie-tool.py build all -e --docker-repo <example:5000> --docker-logs --insecure -o artie-tool-log.txt`

This command will invoke the `build` subcommand of Artie Tool with `all` as its target. Artie Tool has several
different subcommands:

* [**build**](#artie-tool-build): Build Docker images, Yocto images,
  or firmware and output the build artifacts into the build-artifacts directory.
* [**release**](#artie-tool-release): Create an official release. This is not yet implemented and might get removed.
* [**test**](#artie-tool-test): Run sanity tests, unit tests, integration tests, and hardware tests.
* [**flash**](#artie-tool-flash): Flash FW onto an MCU directly or a Yocto image onto an SD card.
* [**install**](#artie-tool-install): Install an Artie (typically it is a better experience to use Workbench for this task).
* [**uninstall**](#artie-tool-uninstall): Uninstall an Artie.
* [**deploy**](#artie-tool-deploy): Deploy a Helm Chart to an installed Artie.
* [**status**](#artie-tool-status): Get the status of an Artie.
* [**get**](#artie-tool-get): Get certain values from an installed Artie (this is mostly for programmatic use).
* [**clean**](#artie-tool-clean): Clean up.

The overarching flow of Artie Tool is this:

1. Artie Tool parses all of the available tasks in the tasks directory. This happens regardless of which
   task is chosen as the target.
1. The application determines the target task from the input arguments.
1. The target task's dependencies are evaluated recursively, adding all required tasks to the queue, which
   is then sorted topologically, and each task is checked to see if its artifacts are already ready
   from a previous run. If so, the task is removed from the queue.
1. Artie Tool then executes tasks in the appropriate order, parallelizing by Python's multiprocessing
   library, with one process per task, up to some limit specified by command line (defaulting to the
   number of cores on the development machine). During this, artifacts are passed down to the
   tasks that require them.

### Artie Tool: Build

The `build` subcommand of Artie Tool allows you to build various components of Artie. Try running
`python artie-tool.py build --help` to see all the options, including the available targets.

The targets are populated by the build tasks defined in the `framework/artietool/tasks/build-tasks/` directory.

See [the task specification document](../../framework/artietool/tasks/README.md#build) for more information on how to
define new build tasks.

Of note:

* Firmware images are built inside Docker containers for easy reproducibility and to keep dependencies
to a minimum. After building the Docker image that contains the target FW image, the Docker image is
run as a container and another process takes the FW binary from the running container and puts it
in the artifact directory.
* Docker images are built, often as manifest lists, and pushed to your development registry.
* Yocto images are not built by default, because they are a massive undertaking that requires
an enormous number of installed dependencies, disk space, and time.
See [the Yocto document](./yocto-image-contributions.md).

### Artie Tool: Release

The `release` subcommand of Artie Tool automates the process of packaging up a release. At least that's the idea,
but it will likely be removed in the future.

### Artie Tool: Test

The `test` subcommand of Artie Tool automates tests.

The targets are populated by the test tasks defined in the `framework/artietool/tasks/test-tasks/` directory.

See [the task specification document](../../framework/artietool/tasks/README.md#test) for more information on how
to define new test tasks.

Of note:

* Types of tests:
    - Sanity tests: These tests just make sure that a component starts without crashing. This type
      of test starts a container and just ensures that it doesn't immediately exit with a non-zero
      exit code.
    - Unit tests: These tests attempt to ensure the API functions all seem to work properly.
      These tests typically work by starting a Docker container (a Docker container under test or 'DUT'),
      then running Artie CLI inside its own Docker container so that it makes an API call into
      the DUT, then checking for a particular log message in the DUT or CLI container.
    - Integration tests: These tests utilize Docker Compose to start up more than one DUT, then they
      run an API call from Artie CLI inside a container in the Compose network and check each expected
      message is logged.
    - Hardware Tests: These tests assume a running Artie K3S cluster and create a Kubernetes job. It's
      been a while since I've run one of these... so I don't remember how they work exactly. See the
      module documentation in `hardware_test_job.py` for some explanation.
* Tests should be designed to allow as much parallelization between different tests as possible
  and so that failing one test does not cause downstream failures that are hard to understand.

### Artie Tool: Flash

The `flash` subcommand of Artie Tool allows a developer to flash FW images onto MCUs directly
(this is useful for development, but in a real Artie, the FW images are flashed to the MCUs
by means of CAN bus from Docker containers deployed to the cluster). It also allows a developer
to flash an SD card with a Yocto image - this is useful in development mostly, as the Yocto images
are equipped with an over-the-air update mechanism, however, the end user will need to flash
the images at least once manually, and they could use this tool to do so. Another good option
is the program Etcher.

The targets are populated by the flash tasks defined in the `framework/artietool/tasks/flash-tasks/` directory.

See [the task specification document](../../framework/artietool/tasks/README.md#flash) for more information on how
to define new test tasks.

### Artie Tool: Install

The `install` subcommand of Artie Tool allows a developer to install a new Artie.

Each Artie instance is managed by an Artie Profile - a JSON file stored to the user's/developer's
hard drive. This JSON file is managed entirely by Artie Tool and Artie Workbench and in practice,
a user/developer should never need to know it even exists or where to find it. The stuff
it contains and the Python code managing it can be found in
`framework\libraries\artie-tooling\src\artie_tooling\artie_profile.py`

Installing an Artie is easily done through the Workbench application, and end users and developers
alike should use that route whenever possible.

### Artie Tool: Uninstall

The `uninstall` subcommand of Artie Tool allows a developer to uninstall an Artie.

### Artie Tool: Deploy

The `deploy` subcommand of Artie Tool allows a developer to deploy a Helm chart to a particular
Artie.

The targets are populated by the deploy tasks defined in the `framework/artietool/tasks/deploy-tasks/` directory.

See [the task specification document](../../framework/artietool/tasks/README.md#deploy) for more information on how
to define new test tasks.

### Artie Tool: Status

The `status` subcommand of Artie Tool is useful mostly programatically. Use Workbench to
view the status of an Artie cluster.

### Artie Tool: Get

The `get` subcommand of Artie Tool is useful mostly programatically.

### Artie Tool: Clean

The `clean` subcommand of Artie Tool cleans up all the build artifacts.
