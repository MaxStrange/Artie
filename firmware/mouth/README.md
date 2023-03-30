# Mouth FW

This directory contains the stuff associated with the mouth microcontroller unit.

## Building

Instructions for building:

1. Change directory into the build folder.
1. Run `docker build -f Dockerfile -t artie-mouth:$(git log --format="%h" -n 1) ../..`