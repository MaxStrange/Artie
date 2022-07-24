# Building the Neural Module - Ears

The neural module for the ears uses a custom Linux image build using [Yocto](https://www.yoctoproject.org/).
We make use of Docker for this, so that you don't need a Linux build system to build the image.

## Prerequisites

* Docker
* Space on your HD: at least ~20GB (it takes a lot of space to custom build a Linux image) - don't worry, you
  can have the space back after you are done with the build.
* Micro SD card for the Jetson Nano - at least 2GB in size; they are pretty cheap, so just buy a decently large one
  and save yourself the worry about running out of space.

## Steps

1. Make sure Docker is running, then from this directory, run `docker build -t neural-module-ears:$(git log --format="%h" -n 1) .`
   This will take a few hours.