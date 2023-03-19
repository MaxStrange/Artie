# Mouth/Eyebrow Drivers

This folder contains the source for both user-space drivers: eyebrows and mouth.
It also contains a single Dockerfile and build script which is shared by both drivers.

## Build Instructions

Just run `python build.py <driver> <firmware-docker-image>` from this directory, where:

* `driver` is one of 'mouth' or 'eyebrows'
* `firmware-docker-image` is a previously built Docker image (see the appropriate instructions below).
  Please note that this image *must* be from a *remote* Docker registry, as buildx cannot ingest
  local images for cross compilation (at least, as of this writing).
    * For the mouth FW image: [see these build instructions](../../firmware/mouth/README.md)
    * For the eyebrow FW image: [see these build instructions](../../firmware/eyebrows/README.md)
