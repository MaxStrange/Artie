# Building Artie

This guide shows you how to build Artie from scratch.

## Prerequisites

You will need the following items:

* A host computer - the computer can be running any OS that supports git and Docker
* This repository - this repo contains all the code and instructions
* A 3D printer - as many of the parts as possible are 3D-printable using a small budget 3D printer
* Docker - to make things reproducible, we will be using Docker for building the firmware
* [Parts](./parts-list.md) - unfortunately, some parts just can't be built - you have to buy them yourself. See here for a bill of materials (BOM)
* Soldering equipment - you are going to have to get your hands dirty to put the circuit boards together

## Get the circuit boards

To procure the circuit boards:

1. Find and buy all the electrical components you need from the [BOM](./parts-list.md).
1. Send the gerber files to a fab place like [OSH Park](https://oshpark.com/) which can make the circuit boards cheaply.
   You can find a link to the gerbers for the circuit boards in the [BOM](./parts-list.md).

## 3D Print Stuff

Fire up your 3D printer and print all the items found in the [3D-printable parts list](./3d-printable-parts-list.md)
for the release you plan on building.

## Assembly

Artie is composed of modules, wires, and a frame. Each module contains its own building instructions in the mechanical folder,
which you should be able to find by going through the [3D-printable parts list](./3d-printable-parts-list.md).

As a part of building Artie, you will need to build each module's firmware and flash that firmware to the modules.
Because we are using Docker to automate this, it shouldn't be as daunting as it sounds. Follow the instructions
in each part's guide and you should be fine.

After each separate part has been built, you can combine them all by following these instructions:

TODO

Congratulations! You now have a functioning Artie.