# Chart Contributions

[Back to Artie Workbench Contributions](./artie-workbench-contributions.md) | [Forward to Simulator Contributions](./simulator-contributions.md)

This document provides guidelines and best practices for contributing
Helm Charts to the Artie project.

## Overview of Helm Charts

The Helm Charts are the way that any Docker image ever gets deployed to a physical Artie.

Once your Artie has the required Yocto images on its SBCs and bootloaders
on its MCUs, you should be able to update its software workload by means
of Helm Chart deployment.

The Helm Charts that we oficially provide for Arties currently
live in each component's `deploy/` directory (for example `framework/ardk/deploy/`) (along
with an AI-written [HELM OVERVIEW](../../framework/ardk/deploy/HELM_ARCHITECTURE.md), which is probably good reading for this).

[Back to Artie Workbench Contributions](./artie-workbench-contributions.md) | [Forward to Simulator Contributions](./simulator-contributions.md)
