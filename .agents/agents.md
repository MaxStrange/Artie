# Artie Project — Agent Guidelines

The Artie Project is a multi-repository software and hardware endeavor that seeks to
enable low(ish) cost research and development in the area of developmental robotics, particularly
by citizen scientists.

## Repositories

* **Artie** — landing page for the project; holds documentation
* **Artie00** — current best reference robot built using Artie Framework; seeks to emulate a neonatal human
* **ArtieCLI** — a CLI program for low-level testing of Artie Framework and Artie robot components
* **ArtieDaemons** — daemons that run Artie cluster infrastructure on off-robot computers
* **ArDK** — Artie Development Kit; libraries that can be used by many different robots
* **ArtieTool** — a CLI program for managing an instance of Artie Framework (the Kubernetes cluster, the build, the deployment, etc.)
* **ArtieWorkbench** — a GUI program for more convenient management of Artie Framework compared to ArtieTool, and for experiment management
* **artie-controller-node** — Yocto build for a Raspberry Pi for use with Artie00 (and for others if they would like to use it)

Each of these repositories has its own `.agents/agents.md`. Before doing any work in any of
those repos, read the guidelines there first.

## Major Components

1. **Artie00** — the current robot we are working on. Serves as a reference for others to use
   Artie Framework and will be used for research into cognitive development of human infants.
2. **Artie Framework** — the tools and SDK used for building Artie00 but can be used for
   building any robot whose main purpose is scientific experimentation and data collection.

## Typical User Workflow

* Create a custom robot using Artie00 as a reference, following our design guidelines and using our SDK
* Run experiments using our tools
* Collect data and do analysis

This is a large and complicated project, and it is important that humans be able to read and
reason with the docs and code. The design constraints and conventions below apply to all work
in this repository.

## Design Constraints

* Builds are done using ArtieTool.
* Tests are run using ArtieTool. There are sanity tests, unit tests, integration tests, and
  eventually, hardware tests.
* All code changes must (ultimately) pass the full suite of tests.
* All Artie Framework-compliant robots have at least a controller node, which does not have to
  be our Yocto image.
* Read the docs in this repository to get a good understanding of further constraints before
  writing any tasks, unless explicitly told otherwise.
