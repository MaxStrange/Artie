# Chart Contributions

This document provides guidelines and best practices for contributing
Helm Charts to the Artie project.

## Overview of Helm Charts

The Helm Charts are the way that anything ever gets deployed to a physical Artie.

Once your Artie has the required Yocto images on its SBCs and bootloaders
on its MCUs, you should be able to update its software workload by means
of Helm Chart deployment.

The Helm Charts that we oficially provide for Arties currently
live in `framework/artietool/deploy-files/` (along
with an AI-written [HELM OVERVIEW](../../framework/artietool/deploy-files/HELM_ARCHITECTURE.md), which is probably good reading for this).
