# Base Image

This folder contains the Dockerfile for building the base Docker image
used by most Artie container components. By having a single base image,
it makes it easier to upgrade the whole system, keep track of dependencies,
and cut down on boilerplate/copy-paste.

This folder additionally contains any other Dockerfiles for base components
common to more than one image, such as OpenOCD.
