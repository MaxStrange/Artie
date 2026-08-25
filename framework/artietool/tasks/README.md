# Task Configuration File Specification

A task file is a YAML file that conforms to the following specification.

```yaml
name: driver-eyebrows
labels:
    - docker-image
dependencies:
    - fw-eyebrows: fw-files
    - artie-base-image: docker-image
cli-args: []
artifacts:
    - name: docker-image
      type: docker-image
type: build
# ...
```

## Top-Level Keys

- *name*: The task name. This will be the name that is displayed and used by the CLI and
          is the value by which other tasks can access this task's artifacts.
- *labels*: A set of labels which the CLI uses for task discovery and classification.
- *dependencies*: A list of key-value pairs of the form {task-name: artifact-name}, where
                  `task-name` is the name of the task that produces the desired artifact
                  and `artifact-name` is the name of the artifact, which may be an empty string.
- *artifacts*: A list of [artifact](#artifact) items.
- *cli-args*: Additional arguments to add to the CLI. The keys are python argparse.add_argument parameters.
- *type*: One of
    * [build](#build)
    * [test](#test)
    * [flash](#flash)
    * [deploy](#deploy)

## Artifact

An *artifact* is composed of the following items:

- *name*: The name of the artifact. This is how dependent tasks reference this artifact.
          Conventionally, this is the same as the type, but can be different, especially
          if a task produces more than one of the same type of artifact.
- *type*: The type of artifact produced. The type can be one of:
    * *docker-manifest*: A Docker manifest list. This should be able to be interpreted by anything and everything in a transparent way
                         by treating it as a Docker image - it is just secretly more than one image and the appropriate image is chosen
                         based on the machine architecture.
    * *docker-image*: A Docker image name (including tag and repo); the name of the image produced is specified in the `steps` (see below).
    * *files*: A collection of one or more files.
    * *yocto-image*: A Yocto image binary.
    * *helm-chart*: A Helm chart that has been deployed to the cluster.

## Script Definition

A *script definition* is a way of specifying a script to run. It can be one of the following:

- *script-path*: A path to a script file. This can be either an absolute path or a path relative to the root of the Artie repository.
- *cmd*: A command string to run directly.

It has an optional key:

- *args*: A list of arguments to pass to the script or command.
          For each item, if it is a string, it will be passed as a positional argument.
          If it is a key:value pair, the key will be treated as the argument name (e.g., `--flag`)
          and the value will be treated as the argument value.

Either way, the script will be run inside a shell (i.e., `/bin/bash -c "<script-path or cmd>"`)
and will be passed any arguments specified in the `args` list.

## Build

Example:

```yaml
steps:
  # The subtype of task for this step (all steps must be a subtype of the top-level type)
  - job: docker-build
    # Args for docker-build type job
    ## The artifacts we are producing with this job
    artifacts:
        - docker-image
    ## The base (simplified) name of the produced docker image
    img-base-name: artie-eyebrow-driver
    buildx: true
    platform: linux/arm64
    dockerfile-dpath: "${REPO_ROOT}/artie-common/drivers/mouth-and-eyebrows"
    dockerfile: Dockerfile
    build-context: "."
    dependency-files:
      - dependency:
        name: fw-files
        producing-task: fw-eyebrows
        match: "*.elf"
    build-args:
      - DRIVER_TYPE: eyebrows
      - FW_FILE_NAME:
          dependency:
            # The resulting FW_FILE_NAME will be a string that points to a file in the build context (we will copy it from the artifact location)
            name: fw-files
            producing-task: fw-eyebrows
            # We only take files that match the pattern *.elf
            match: "*.elf"
      - SERVICE_PORT: 18861
      - GIT_TAG: ${GIT_TAG}
      - ARTIE_BASE_IMG:
          dependency:
            # We will use the actual name of the docker image produced by the pre-requisite task
            name: docker-image
            producing-task: artie-base-image
```

- *steps*: A list of `job` items, each of which must be one of the following:
    * [docker-build](#docker-build-job)
    * [file-transfer-from-container](#file-transfer-from-container)
    * [yocto-build](#yocto-image-job)
    * [docker-manifest](#docker-manifest)

### Docker Build Job

- *artifacts*: The names of the artifacts that we are producing with this job, which must include at least one docker-image type.
- *img-base-name*: The name of the image to be produced, without the repo or tag.
- *buildx*: (Optional, default false) Boolean. If true, we will use Docker buildx to produce the image. Otherwise it is built
            using the host machine's default driver.
- *platform*: (Optional, default linux/arm64) String. If `buildx` is true, you should specify this value as the platform to build for.
            Should be a string of the form 'linux/arm64' or 'linux/amd64'.
- *dockerfile-dpath*: The directory where we will find the Dockerfile.
- *dockerfile*: (Optional, default 'Dockerfile') The name of the Dockerfile, which should be found at `dockerfile-dpath`.
- *build-context*: (Optional, default '.') The build context to use when building, which should be *relative* to the `dockerfile-dpath`.
- *dependency-files*: (Optional) A list of `dependency` items which should evaluate to files we will copy
  into the build context (in a directory called 'tmp' inside the build context, to be precise) before running the Dockerfile.
  OR a list of hard-coded string values, which are the file paths. Can be files or directories, despite the name.
- *build-args*: (Optional) A list of `build-arg` items, which are either key:value pairs passed via --build-arg to the
                Docker build command, or are `dependency` items produced by dependency tasks, and follow this specification:
    * *name*: The name of the artifact that this build-arg depends on.
    * *producing-task*: The name of the task that produces the artifact that this build-arg depends on.
    * *match*: (Optional) If the artifact we require for this build-arg produces a list of files (it is of `files` type),
               you can filter out the files you need by using a regular expression here. Match should produce exactly one file.

### File Transfer From Container

We build our firmware files by first building a Docker image,
then starting that image as a container, which should build the firmware files.

- *artifacts*: The names of the artifacts which are created by this job, at least one of which must be of the type `fw-files`.
- *image*: Composed of a `dependency` item or a string name of the Docker image to pull (if a public image).
- *fw-files-in-container*: The list of file paths to copy out of the container. These will be the fw-files artifact that this job produces.

### Yocto Image Job

Yocto images are built by:

1. Cloning a remote Git repository that contains all the necessary Yocto recipes.
1. Cloning a set of Yocto layers specified in the job configuration.
1. Running a setup script to set up the Yocto build environment.
1. Running the Yocto build command to create the desired image.
1. Running a post-build script to create the final image file.

- *artifacts*: The names of the artifacts which are created by this job, at least one of which must be of the type `yocto-image`.
               The produced image will be the *.img file specified by `binary-fname`.
- *repo*: The Git repository to clone. This repo should contain all the necessary Yocto recipes to build the desired image.
- *repo_name*: The name of the repository once cloned. This is used to construct the path to the cloned repository.
- *layers*: A list of Yocto layers to clone into the repository before building. Each layer should be specified as a dictionary of *name* mapped to the following items:
    * *url*: The Git URL of the layer.
    * *tag*: (Optional) The Git tag to checkout.
- *setup-script*: A script definition that specifies the setup script to run before building.
                  This script should set up the Yocto build environment (other than cloning things,
                  which will already have been done by this point). This script definition can
                  be relative, and if so, it will be relative to the root of the cloned repository.
- *build-cmd*: A script definition that specifies the build command to run to build the Yocto image.
                This command will typically source poky/oe-init-build-env and invoke `bitbake`
                with the desired image target, which can be specified via the `${YOCTO_IMAGE}` constant.
                See `--yocto-image` CLI argument below. This script definition can
                be relative, and if so, it will be relative to the root of the cloned repository
- *post-script*: A script definition that specifies the post-build script to run after building.
                 This script will typically create the final image file. This script definition can
                 be relative, and if so, it will be relative to the root of the cloned repository.
- *binary-fname*: The name of or relative path to the *.img file. If a relative path,
                  it will be relative to the root of the cloned repository. This can make use of
                  the `${YOCTO_IMAGE}` constant to specify the image target name.

CLI arguments:

- *--yocto-image*: The image target to build. This can be referenced in the Yocto job configuration file
                   via the `"${YOCTO_IMAGE}"` constant.
- *--repos-directory*: (Optional, default '../') The directory in which to clone the repository. This can be either
                       an absolute path or a path relative to the root of the Artie repository.
- *--repo-branch*: (Optional, default 'main') The branch of the repository to clone.
- *--skip-clone*: (Optional, default False) If set, skip cloning the repository. If the repository already exists and this
                  is NOT passed, an error will be raised to prevent overwriting existing work.
- *--yocto-hosts*: (Optional, default {}) If given, should be a comma-separated list of items of the form "host-name:host-address".
                  These items will be added to the Yocto image's /etc/hosts file.
- *--yocto-insecure-registries*: (Optional, default []) If given, should be a comma-separated list of insecure Docker registries
                                 that will end up in the Docker configuration file on the target image.

### Docker Manifest

A Docker manifest is a list of multiple images, each of which might be run on a different architecture.
See the [official documentation](https://docs.docker.com/engine/reference/commandline/manifest/).
The created manifest list's name will be based on `img-base-name` in a way analogous to how it is done in Docker build jobs -
i.e., the repo and tag will be passed in or inferred at runtime and appended to the manifest's name.

- *artifacts*: The names of the artifacts which are created by this job, at least one of which must be of the type `docker-manifest`.
- *img-base-name*: The base name of the manifest without the repo or tag.
- *images*: The list of images that this manifest list is composed of. Should be a list of images, each of which can be
            either a hard-coded string name of the Docker image or a `dependency`.

## Test

Example:

```yaml
name: eyebrows-driver-unit-tests
labels:
  - docker-image
  - sanity
dependencies:
  - eyebrows-driver-sanity-tests: ""
  - driver-eyebrows: docker-image
  - artie-cli: docker-image
type: test
steps:
  - job: single-container-cli
    docker-image-under-test:
      dependency:
        name: docker-image
        producing-task: driver-eyebrows
    cmd-to-run-in-dut: "python main.py /conf/mcu-fw.elf --port 18863 --loglevel info --mode unit"
    dut-port-mappings:
      - 18863: 18863
    cli-image:
      dependency:
        name: docker-image
        producing-task: artie-cli
    - test-name: init-mcu
      cmd-to-run-in-cli: "artie-cli help"
      expected-outputs:
        - what: "Mocking MCU FW Load."
          where: ${DUT}
    - test-name: led-on
      cmd-to-run-in-cli: "artie-cli eyebrows led on --side left"
      expected-outputs:
        - what: "Left LED -> ON"
          where: ${DUT}
```

All tests start with:

- *name*: Same as for [build](#build)
- *labels*: Same as for [build](#build)
- *dependencies*: Same as for [build](#build)
- *type*: test
- *steps*: A list of jobs, each of which should be a complete test *suite*. Setup and teardown bookends
           a test suite. Typically, if a test fails inside a suite, all the following tests in that same
           suite are marked as did-not-run and are skipped.

Available job values:

* [single-container-sanity-suite](#sanity-test-job)
* [single-container-pytest-suite](#pytest-test-job)
* [single-container-cli-suite](#unit-test-job)
* [docker-compose-test-suite](#integration-test-job)
* [hardware-test-job](#hardware-test-job)

### Sanity Test Job

A sanity test job looks like this:

- *job*: single-container-sanity-suite; this runs a single Docker container with a given command to completion or timeout.
         Success is counted if it does not throw an exception or timeout.
- *steps*: The following items describe a single test within the suite:
  - *test-name*: The name of the individual test.
  - *docker-image-under-test*: The `DUT` (Docker image Under Test). Can be either a `dependency`
          (with name and producing-task) or a hard-coded Docker image name.
  - *cmd-to-run-in-dut*: The command to execute in the DUT. This command will run to completion or timeout.

### Pytest Test Job

A pytest test job runs a whole test suite once inside a Docker container and then checks that container's
output for each individual test's pass/fail status
(see [artie-can-python-unit-tests](./test-tasks/libraries/artie-can-python-unit-tests.yaml)). Despite the
name, the suite doesn't have to be a pytest suite - anything that runs the tests and prints a recognizable
line per test works, such as `ctest -V` over a Unity suite
(see [artie-can-unit-tests](./test-tasks/libraries/artie-can-unit-tests.yaml)):

- *job*: single-container-pytest-suite; this runs the suite once inside a Docker container,
         then checks the container's output for each individual test result. Each test is tracked separately in the final test report.
- *docker-image-under-test*: The `DUT` (Docker image Under Test). Can be either a `dependency`
          (with name and producing-task) or a hard-coded Docker image name. The image should have the test
          runner and the test files present. The container is expected to run the suite and then exit - we wait
          for it to finish (up to `--test-timeout-s`) before checking its output.
- *cmd-to-run-in-dut*: (Optional) The command to run in the container (e.g., `"pytest tests/ -v --tb=short"`).
          If omitted, the image's default command is used.
- *steps*: Each step represents one individual test that you want to track separately:
  - *test-name*: The name of the individual test (should match the test function name).
  - *expected-outputs*: A list of `what` and `where` entries that define what output indicates test success.
      * *what*: The string to expect in the output/logs (typically `"test_name PASSED"`).
      * *where*: The container we are reading from (typically `${DUT}`).
  - *unexpected-outputs*: (Optional) A list of `what` and `where` entries that indicate test failure.

**Example:**
```yaml
steps:
  - job: single-container-pytest-suite
    docker-image-under-test:
      dependency:
        name: docker-image
        producing-task: my-library-test-image
    cmd-to-run-in-dut: "pytest tests/ -v --tb=short --color=yes"
    steps:
      - test-name: test_initialization
        expected-outputs:
          - what: "test_initialization PASSED"
            where: ${DUT}
      - test-name: test_basic_operations
        expected-outputs:
          - what: "test_basic_operations PASSED"
            where: ${DUT}
      - test-name: test_edge_cases
        expected-outputs:
          - what: "test_edge_cases PASSED"
            where: ${DUT}
```

**Note:** Each pytest test must be listed individually in the YAML to be tracked in the test results. This requires maintaining the YAML file when tests are added or removed, but provides detailed per-test reporting.

### Unit Test Job

- *job*: single-container-cli-suite; this sets up a single Docker container and runs a given command in it,
         which will typically be a long-running job that is not expected to complete.
         Then, for each test in the suite, it runs a CLI Docker image with a given command and checks the output in both containers.
         Finally, it tears down the running container.
- *docker-image-under-test*: The `DUT`, as [above](#sanity-test-job).
- *cmd-to-run-in-dut*: The command to run inside the DUT.
- *dut-port-mappings*: (Optional) List of key/value pairs of ports inside container to map to ports on host machine.
- *cli-image*: Like *docker-image-under-test*, but should produce (or be) an ArtieCLI image.
- *steps*:
  - *test-name*: The name of the individual test.
  - *cmd-to-run-in-cli*: The command to run in the CLI container.
  - *expected-outputs*: A list of `what` and `where`.
      * *what*: The string to expect in the output/logs.
      * *where*: The container we are reading from to find the `what`. Should be either a `dependency`, `${DUT}`, or `${CLI}`.

### Integration Test Job

- *job*: docker-compose-test-suite; this runs a Docker compose file, then for each test, runs a CLI Docker image with a given command and
         checks the output in whichever containers as specified.
- *compose-fname*: The name of the Docker compose file. All files should be found in the `compose-files` directory.
- *compose-docker-image-variables*: A list of the form *VALUE-TO-REPLACE-IN-FILE*: `dependency` or hard-coded value.
- *cli-image*: As [above](#unit-test-job).
- *steps*:
  - *test-name*: The name of the individual test.
  - *setup-cmds*: (Optional) A list of commands to run before the main test command. Each command runs in its own CLI container.
                  Useful for setting up test data or preconditions.
  - *cmd-to-run-in-cli*: The command to run in the CLI container. This is used for single-command tests.
                         **Cannot be used together with `parallel-cmds`**.
  - *parallel-cmds*: (Optional) A list of commands to run in parallel, each in its own CLI container.
                     Useful for testing scenarios like multiple subscribers or consumer groups.
                     **Cannot be used together with `cmd-to-run-in-cli`**.
      * *cmd*: The command to run in this parallel CLI container.
      * *expected-outputs*: A list of `what` items (strings) expected in this parallel command's output.
      * *unexpected-outputs*: (Optional) A list of `what` items (strings) that should NOT appear in this parallel command's output.
  - *expected-outputs*: (For single-command tests) As [above](#unit-test-job), but `where` cannot be `${DUT}`, but may be a container name as specified
                        in the compose file.
  - *unexpected-outputs*: (Optional, for single-command tests) A list of outputs that should NOT appear in the container logs.
      * *what*: The string that should NOT be found in the output/logs.
      * *where*: The container we are checking. Should be a container name from the compose file or `${CLI}`.
  - *teardown-cmds*: (Optional) A list of commands to run after the test completes (success or failure). Each command runs in its own CLI container.
                     Useful for cleanup. These commands will run even if the test fails.

**Example with single command:**
```yaml
- test-name: subscribe-and-receive-message
  setup-cmds:
    - 'artie-cli service publish test-topic ''{"message": "test"}'' --integration-test'
  cmd-to-run-in-cli: "artie-cli service subscribe test-topic --count 1 --timeout 10 --integration-test"
  expected-outputs:
    - what: '"message": "test"'
      where: artie-cli
  teardown-cmds:
    - 'artie-cli service delete-topic test-topic --integration-test'
```

**Example with parallel commands:**
```yaml
- test-name: multiple-subscribers-same-topic
  setup-cmds:
    - 'artie-cli service publish test-topic ''{"message": "broadcast"}'' --integration-test'
  parallel-cmds:
    - cmd: "artie-cli service subscribe test-topic --count 1 --timeout 10 --integration-test"
      expected-outputs:
        - what: '"message": "broadcast"'
    - cmd: "artie-cli service subscribe test-topic --count 1 --timeout 10 --integration-test"
      expected-outputs:
        - what: '"message": "broadcast"'
```

**Example with unexpected-outputs:**
```yaml
- test-name: topic-isolation
  setup-cmds:
    - 'artie-cli service publish topic-a ''{"topic": "a"}'' --integration-test'
  cmd-to-run-in-cli: "artie-cli service subscribe topic-b --count 1 --timeout 5 --integration-test"
  expected-outputs:
    - what: "Subscribed to topic"
      where: artie-cli
  unexpected-outputs:
    - what: '"topic": "a"'
      where: artie-cli
```

Note that Docker compose tests require compose files, and these compose files MUST include a `networks` section that
specifies a Docker network that the test will create. Since the test creates it, it should be labeled in the Compose
file as `external`. See the example Compose files.

### Hardware Test Job

All hardware tests selected by the user are collected and run in a single Kubernetes job on the Artie cluster.

- *job*: hardware-test-suite
- *steps*:
  - *test-name*: The name of the individual test.
  - *cmds-to-run-in-cli*: The commands to run in the CLI continer. This is a list of strings, each of which will typically be of the form 'artie-cli <module> self-test'
  - *expected-results*: How to interpret the output from the CLI command. Should be a dict of key values, which should match the
  format of the output of the self-test command in terms of the
  submodule. For example: `LED-LEFT: "working"`

## Flash

All flash tasks start with:

- *name*: Same as for [build](#build)
- *labels*: Same as for [build](#build)
- *dependencies*: Same as for [build](#build)
- *cli-args*: Same as for [build](#build)
- *type*: flash
- *steps*: A list of `job` items, each of which must be one of the following:
    * [yocto-flash](#yocto-flash-job)

CLI arguments:

- *--device*: (Required) The path to the device (e.g., /dev/sdX) to flash the Yocto image onto.
- *--yocto-image*: The image target to use. This should match the name of a Yocto image
                   produced by a dependency task. If `image` is a hard-coded path,
                   this argument is ignored (but is still required due to parsing the dependency task).


### Yocto Flash Job

- *job*: yocto-flash; This flashes a Yocto image onto a given device (typically an SD card).
- *image*: A `dependency` item that produces a `yocto-image` artifact
           OR a hard-coded path to a Yocto image file, which may be either absolute or relative to the root of the Artie repository.

## Deploy

All deployments start with:

- *name*: Same as for [build](#build)
- *labels*: Same as for [build](#build)
- *dependencies*: Same as for [build](#build)
- *cli-args*: Same as for [build](#build)
- *type*: deploy
- *steps*: A list of `job` items, each of which must be one of the following:
    * [add](#add-deployment-job)

CLI arguments:

- *--release-name*: (Optional, defaults to `what` from the below definition of the `Add Job`).
  The name of the Helm release to deploy to the cluster.
- *--chart-path*: (Optional, defaults to the `chart` from the below definition of the `Add Job`).
  The path to the Helm chart to deploy. This can be either an absolute path or a path relative to the root of the Artie repository.

### Add Deployment Job

- *job*: add; This adds a deployment.
- *what*: The name of the Helm deployment. This should be one of:
    * *artie-base*: The common set of containers that other deployments typically depend on.
    * *artie-teleop*: The set of containers required to run the [teleop](../../docs/out-of-the-box/teleop.md) workload.
    * *artie-demo*: The set of containers required to run the [demo stack](../../docs/out-of-the-box/deploy-demo.md) workload.
    * *artie-reference*: The set of containers required to run the [reference stack](../../docs/out-of-the-box/deploy-artie-reference-stack.md) workload.
    * *artie-custom*: A custom deployment defined by the user. The name will typically be passed in as an argument
    (see `--release-name` CLI argument above). TODO: Document this option like the others.
- *chart*: Path to the chart, relative to artietool directory. E.g., `deploy-files/artie-teleop`, OR `${CHART_PATH}`
  to use the path from the CLI argument.

## Constants

These values can be used inside of a `${}` in order to signal
that they should be replaced with something special, usually known
only at runtime. Here are the available values:

- `REPO_ROOT`: This value will be replaced with the root of the Artie repository.
- `GIT_TAG`: This value will be replaced with the git hash (short form).
- `DUT`: This value will be replaced with the Docker image under test, for scenarios where a single Docker image is being tested.
- `CLI`: This value will be replaced with the CLI Docker image,
         for scenarios where a single CLI Docker image is expected.
