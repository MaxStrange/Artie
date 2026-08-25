# Setting up a Development Environment

[Back to Overall Architecture](./overall-architecture.md) | [Forward to Electronic Design](./electronic-design.md)

This document provides instructions for setting up a development environment for contributing to the Artie project.
These instructions closely mirror those used by an end-user to set up and administer an Artie, but with
a few additional steps that are useful for development.

Hence, first follow the instructions found in
[the Building Artie Guide](../building/building-artie-main.md#setting-up-your-development-computer)

Once you have followed those instructions, you can set up your development
environment by following these additional steps.

## Set Up a Local Docker Registry

If you develop software for Artie, you will need to build Docker images and push them to a Docker registry
with astonishing size and frequency. Using something like DockerHub is not typically feasible for fast iteration,
as you will hit rate limiting unless you are paying for a plan.

There are myriad ways to set up a local registry, but they are almost all way too complicated and time consuming,
involving nginx and TLS certs that you have to pay for.

**If you are on an untrusted network, you have to deal with all of that.** There's no two ways around it.
If you cannot be sure there is no man in the middle, then you should follow one of the many tutorials
or official guides out there for setting up a Docker registry.

If however, you are on your own local network in your own home, you can probably get away with going
the insecure route. *To be clear, this is insecure*. Don't do it if you cannot guarantee the security of your network.

To do it, follow these steps:

1. Procure a Raspberry Pi or similar.
1. Procure a big ol' SSD.
1. Mount the SSD permenantly. Do **not** just let your desktop environment automount it under
   `/media/<user>/<label>` - that path only appears once you log in, which means it is *not* mounted
   at boot when the registry container starts. See
   [Registry storage and /etc/fstab](#registry-storage-and-etcfstab) below for how to do this properly;
   getting it wrong silently fills up your root partition.
1. Make a directory: `mkdir docker-registry`
1. Change into that directory: `cd docker-registry`
1. `mkdir certs`
1. Create a self-signed cert, good for 10 years (here this machine is called artiehub, but you should use whatever your machine's hostname is):
    ```bash
    openssl req -newkey rsa:4096 -nodes -sha256 -keyout certs/domain.key \
      -addext "subjectAltName = DNS:artiehub" \
      -x509 -days 3650 -out certs/domain.crt`
    ```
1. Create a Docker registry configuration file called config.yml:
    ```yaml
    version: 0.1
    log:
      level: info
      fields:
        service: registry
    storage:
      cache:
        blobdescriptor: inmemory
      filesystem:
        rootdirectory: /var/lib/registry
      delete:
        enabled: true
    http:
      addr: :5000
      headers:
        X-Content-Type-Options: [nosniff]
      http2:
        disabled: false
      draintimeout: 60s
      maxrequestbytes: 10485760 # 10 MB
    health:
      storagedriver:
        enabled: true
        interval: 10s
        threshold: 3
    ```
1. Create a script called run-docker-registry.sh:
    ```bash
    docker run --detach \
      -p 5000:5000 \
      --restart=always \
      --name registry \
      -e OTEL_SDK_DISABLED=true \
      -e OTEL_TRACES_EXPORTER=none \
      -e REGISTRY_HTTP_ADDR=0.0.0.0:5000 \
      -e REGISTRY_HTTP_TLS_CERTIFICATE=/certs/domain.crt \
      -e REGISTRY_HTTP_TLS_KEY=/certs/domain.key \
      -v /mnt/artie-registry:/var/lib/registry \
      -v <path to this directory>/config.yml:/etc/docker/registry/config.yml \
      -v <path to this directory>/certs:/certs \
      registry:3
    ```
1. Make the script executable and run it: `chmod +x ./run-docker-registry.sh`, then `./run-docker-registry.sh`.

The `--restart=always` flag is what causes Docker to start the registry again every time the machine
boots up. Be aware that this is a double-edged sword: the container will come back at boot *whether or
not the SSD actually mounted*, and if it didn't mount, the registry will happily write blobs onto your
root partition instead. See [Registry storage and /etc/fstab](#registry-storage-and-etcfstab).

Anyway, you will want to make sure you do the following on your *development machine*:

1. Update your /etc/hosts file (or equivalent on Windows: "C:\Windows\System32\drivers\etc\hosts") to include the name of your registry:
   e.g., `10.0.0.251  artiehub`
1. Update your Docker config JSON with `"insecure-registries": ["artiehub:5000"]`
1. Make sure to pass `--insecure` with any Artie Tool command that makes use of the Docker registry.

### Registry storage and /etc/fstab

The registry's blob storage is a bind mount from the SSD, so how you mount that SSD matters a great deal.
The failure mode here is nasty because it is completely silent: if the SSD is not mounted when the registry
container starts, the container writes into the bare mount point directory, which lives on the Pi's root
partition. Everything looks fine - pushes succeed, pulls succeed - right up until the root partition hits
100% and the machine falls over. Meanwhile `du` will not show you the culprit, because the SSD is now
mounted on top of the data and masking it.

Some rules to avoid this:

* **Don't mount under `/media/<user>/`.** That is the desktop automounter's (udisks) territory, and those
  mounts only happen after that user logs in - long after Docker has started. Use `/mnt` or `/srv` instead.
  Having both an fstab entry and udisks pointed at the same path is also a good way to end up with a doubled
  or unexpected mount.
* **Keep `nofail`, but make Docker depend on the mount.** Without `nofail` a missing drive drops a headless
  Pi into an emergency shell, which is worse than the disease. The fix is not to remove it, but to add an
  explicit ordering dependency so the registry cannot start without its storage. USB storage enumeration on
  a Pi is slow and variable, so a timeout alone will not save you.
* **Use fsck pass `0` for exfat.** There is generally no `fsck.exfat` helper installed, so asking for a pass
  produces boot-time warnings or failures.

A good `/etc/fstab` line looks like this:

```
UUID=<your-uuid>  /mnt/artie-registry  exfat  defaults,noatime,nofail,x-systemd.device-timeout=30,uid=1000,gid=1000,umask=022  0  0
```

Get the UUID from `sudo blkid`. Then make Docker refuse to start unless that mount is live, via
`sudo systemctl edit docker.service`:

```ini
[Unit]
RequiresMountsFor=/mnt/artie-registry
```

Finally, belt and braces: make the bare mount point physically unwritable, so that even if something
bypasses the dependency, the errant write fails loudly instead of quietly eating your root partition.

```bash
sudo umount /mnt/artie-registry 2>/dev/null
sudo chattr +i /mnt/artie-registry   # immutable while unmounted; mounting over it still works fine
sudo systemctl daemon-reload
sudo mount -a
sudo systemctl restart docker
```

One more consideration: **exfat is a mediocre choice for registry storage.** It has no POSIX permissions or
ownership (which is why the `uid`/`gid`/`umask` options above are needed as a blunt global override), no
symlinks or hardlinks, and no journaling, so it is more prone to corruption on the unclean shutdowns a Pi
will eventually experience. If the SSD is dedicated to this machine and doesn't need to be readable on
Windows or macOS, format it `ext4` and drop the `uid`/`gid`/`umask` options.

### Troubleshooting: the registry Pi's root partition is full

If `df -h` shows `/dev/root` at 100%, first find out whether the used space is actually *visible*:

```bash
sudo du -shx /* 2>/dev/null | sort -h
```

Note the `-x`, which stops `du` from wandering onto the SSD and other filesystems. Add up what it reports.
If the total is far less than what `df` claims is used, the space is hidden, and there are really only two
ways that happens:

1. **Files hidden underneath a mount point.** This is the common one, and it means you've hit the problem
   described above. To see the root filesystem with nothing mounted over it, bind mount it somewhere and
   look again:

    ```bash
    sudo mount --bind / /mnt/rootfs
    sudo du -shx /mnt/rootfs/* | sort -h
    ```

   If the SSD's mount point shows up as tens of GB through the bind mount, that's your answer. Before
   deleting anything, confirm you are looking at the hidden copy and not your real registry data:
   `findmnt /mnt/rootfs/<mountpoint>` should report nothing, and `df -h /mnt/rootfs/<mountpoint>` should
   say `/dev/root` rather than the SSD's device. Delete through the bind mount, then `sudo umount /mnt/rootfs`
   and fix the fstab entry so it can't happen again.

   If the disk is so full you cannot even `mkdir /mnt/rootfs`, bind mount onto an existing empty directory
   such as `/mnt` itself.

   Scan the whole sorted list rather than just the SSD's mount point - anything mounted over a subdirectory
   (say, `/var/lib/docker` pointed at the SSD) can mask data the same way, and `/tmp` and `/run` will show
   whatever was written to the on-disk directories before their tmpfs mounts came up.

1. **Deleted-but-still-open files.** A rotated or deleted log that a long-running process still holds open
   keeps its blocks allocated until the process closes the handle.

    ```bash
    sudo lsof +L1 2>/dev/null | awk '{print $7, $NF}' | sort -rn | head -20
    ```

   Check the `DEVICE` column on anything large: `0,1` means anonymous memory (memfd) rather than a block
   device, so those entries are living in RAM and are not your problem. Real offenders are released by
   restarting the process holding them.

Worth checking regardless of the above, since these accumulate on a busy registry host:

```bash
docker info | grep -i "Docker Root Dir"   # is this on the SSD or the root partition?
docker system df -v                       # registry blobs, dangling images, build cache
journalctl --disk-usage                   # then: sudo journalctl --vacuum-size=200M
sudo du -shx /var/* | sort -h | tail
```

Remember that the registry config above sets `delete.enabled: true`, but deleting a manifest through the
API only *marks* blobs as unreferenced. The space is not actually reclaimed until you run garbage
collection:

```bash
docker exec registry bin/registry garbage-collect /etc/docker/registry/config.yml
```

Given how frequently Artie development pushes images, running that periodically is a good idea.

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
`framework/ardk/libraries/artie-tooling/src/artie_tooling/artie_profile.py`

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

[Back to Overall Architecture](./overall-architecture.md) | [Forward to Electronic Design](./electronic-design.md)
