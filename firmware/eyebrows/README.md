# Eyebrow FW

This directory contains the stuff associated with the eyebrow microcontroller units.

## Building

Instructions for building:

1. Change directory into the build folder.
1. Run `docker build -f Dockerfile -t artie-eyebrows:$(git log --format="%h" -n 1) ..`
