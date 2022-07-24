# Building the Controller Module

The controller module uses a custom Linux image built using [Yocto](https://www.yoctoproject.org/).
We make use of Docker for this, so that you don't need a Linux build system to build the image.

## Prerequisites

* Docker
* Space on your HD: at least ~20GB (it takes a lot of space to custom build a Linux image) - don't worry, you
  can have the space back after you are done with the build.
* SD card for the Raspberry Pi - at least 2GB in size; they are pretty cheap, so just buy a decently large one
  and save yourself the worry about running out of space.
* WSL if on Windows

## Steps

1. Build the custom pi.img Linux image by running: `python build.py --delete-image`; this will take several hours.
1. This will create a `pi.img` file. Flash this to your micro SD card using whatever flashing program you like.
1. The first time you boot up the image, it will drop you at a terminal that asks for your username and password.
   Both are `root`. After you login the first time, it will force you to change your password - change it to
   whatever you like.

## TODO:

Changes that need to be made to the Yocto build:

- Enable cgroup_memory in kernel args
- Enable i2c driver in kernel (not sure if this is done by default)
- Enable GPIOs in kernel (not sure if this is done by default)
- Install avahi
- Install k3s binary
  - Configure k3s?
- Install systemd tree like this:
    - avahi discovers artie-* hostnames and resolves them to IP addresses (for Nanos this will be required to happen before the next step)
    - k3s starts as server (agent on Nanos, which requires the hostname for the controller)