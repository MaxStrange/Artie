# Artie

This repository contains the code for a robot that I am slowly working on.

The purpose of Artie is twofold: data collection and testing developmental robotics theories.

The vision is that Artie will be fully open source, 3D-printable, and as cheap as is feasible,
while still being easy to use and extend.

## Get Started

Before you can use Artie, you need to build him.

### Building Artie

Building Artie is composed of the following steps:

1. Get your parts
1. Flash the parts
1. Build your bot

[See here for the full instructions](./docs/building/building-artie-main.md)

### Deploying Experiments

Once you have a functioning Artie, feel free to play around with the following:

* [Command Line Interface (CLI)](./cli/README.md) - this is a way to interface with Artie on a low-level. Use
  this for things like testing his electrical and hardware connections.
* [Use a pre-defined experiment](./docs/deploying/deploying-pre-built-experiments.md) - Artie makes use of experiment
  configuration files to deploy experiments. There are a few already ready to go.
* [Make your own experiment](./docs/deploying/custom-building-experiments.md) - Once you are comfortable with Artie,
  you can start defining your own experiments.

Artie is meant to be used to collect data in real-life social situations as well as to test
theories of developmental robotics.
