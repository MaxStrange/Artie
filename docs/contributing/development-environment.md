# Setting up a Development Environment

This document provides instructions for setting up a development environment for contributing to the Artie project.
These instructions closely mirror those used by an end-user to set up and administer an Artie, but with
a few additional steps that are useful for development.

Hence, first follow the instructions in the [Artie Out of the Box (Edge Deployment)](../out-of-the-box/edge.md) guide.

Once you have followed those instructions and have a working Artie deployment, you can set up your development
environment by following these additional steps.

## Set Up a Local Docker Registry

If you develop software for Artie, you will need to build Docker images and push them to a Docker registry
with astounding size and frequency. Using something like DockerHub is not typically feasible for fast iteration,
as you will hit rate limiting unless you are paying for a plan.

TODO: Describe setting this up, including super obnoxious errors involving insecure registries.

TODO: Describe working with the registry (artie tool command line args, etc.)

TODO: Are there additional steps that differ from the out-of-the-box guide?
