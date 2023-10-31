# Task Configuration File Specification

A task file is a YAML file that conforms to the following specification.

```yaml
name: driver-eyebrows
labels:
    - docker-image
dependencies:
    - fw-eyebrows: fw-files
    - artie-base-image: docker-image
    - open-ocd-image: docker-image
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
- *cli-args*: Additional arguments to add to the CLI. The keys
  are python argparse.add_argument parameters.
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
    dockerfile-dpath: "${REPO_ROOT}/drivers/mouth-and-eyebrows"
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
      - RPC_PORT: 18861
      - GIT_TAG: ${GIT_TAG}
      - ARTIE_BASE_IMG:
          dependency:
            # We will use the actual name of the docker image produced by the pre-requisite task
            name: docker-image
            producing-task: artie-base-image
      - OPENOCD_IMG:
          dependency:
            name: docker-image
            producing-task: open-ocd-image
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
- *dependency-files*: (Optional) A list of `dependency` items which should evaluate to files we will copy into the build context before running the Dockerfile. OR a list of hard-coded string values, which are the file paths. Can be files or directories, despite the name.
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

Yocto images are built by first downloading a remote repository that contains the Yocto layers/recipes,
then running whatever shell scripts. The result should be
a single *.img file suitable for flashing onto an SD card.

*NOTE*: I've never actually tried running this - as the Yocto build is set up on a separate machine. It *might* work, but I
wouldn't hold my breath.

- *artifacts*: The names of the artifacts which are created by this job, at least one of which must be of the type `yocto-image`.
- *repo*: The Git repository to clone.
- *script*: The shell script to run in order to build the *.img file. Note that there is no YAML-level variable expansion for this value.
- *binary-fname*: The name of the *.img file, which must be present at the root of the cloned repository after building.

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
  - *cmd-to-run-in-cli*: The command to run in the CLI continer.
  - *expected-outputs*: As [above](#unit-test-job), but `where` cannot be `${DUT}`, but may be a container name as specified
                        in the compose file.

Note that Docker compose tests require compose files, and these compose files MUST include a `networks` section that
specifies a Docker network that the test will create. Since the test creates it, it should be labeled in the Compose
file as `external`. See the example Compose files.

### Hardware Test Job

- *job*: hardware-test-suite; this depends on a particular helm deployment, then deploys a CLI Docker image which authenticates against
         the cluster that contains the Artie under test. For each test, this CLI Docker image is run with a particular command,
         and the output is checked.
- *cli-image*: As [above](#unit-test-job).
- *steps*:
  - *test-name*: The name of the individual test.
  - *cmd-to-run-in-cli*: The command to run in the CLI continer.
  - *expected-outputs*: As [above](#unit-test-job), but `where` cannot be `${DUT}`, but may be of the form `daemonsets/<name of daemonset>`
  or `deployments/<name of deployment>`
  as specified in the Helm chart.

## Flash

This specification is not yet implemented.

## Deploy

All deployments start with:

- *name*: Same as for [build](#build)
- *labels*: Same as for [build](#build)
- *dependencies*: Same as for [build](#build)
- *type*: deploy
- *steps*: A list of `job` items, each of which must be one of the following:
    * [add](#add-deployment-job)

### Add Deployment Job

- *job*: add; This adds a deployment.
- *what*: One of the following:
    * *artie-base*: The common set of containers that other deployments typically depend on.
    * *artie-teleop*: The set of containers required to run the [teleop](../../docs/out-of-the-box/teleop.md) workload.
    * *artie-demo*: The set of containers required to run the [demo stack](../../docs/out-of-the-box/deploy-demo.md) workload.
    * *artie-reference*: The set of containers required to run the [reference stack](../../docs/out-of-the-box/deploy-artie-reference-stack.md) workload.
- *chart*: Path to the chart, relative to artietool directory. E.g., `deploy-files/artie-teleop`.

## Constants

These values can be used inside of a `${}` in order to signal
that they should be replaced with something special, usually known
only at runtime. Here are the available values:

- `REPO_ROOT`: This value will be replaced with the root of the Artie repository.
- `GIT_TAG`: This value will be replaced with the git hash (short form).
- `DUT`: This value will be replaced with the Docker image under test, for scenarios where a single Docker image is being tested.
- `CLI`: This value will be replaced with the CLI Docker image,
         for scenarios where a single CLI Docker image is expected.
