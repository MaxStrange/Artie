# Versioning and Releases

Artie's components live in separate repositories and version independently. This document
describes how a version is decided, how images get tagged, and how a deployment pins a
combination that is known to work.

## Components

Components version independently.
Each component declares its own version in a `VERSION` file at its repository root:

| Component | Repository |
|---|---|
| ArDK | https://github.com/ArtieBots/ArDK |
| ArtieTool | https://github.com/ArtieBots/ArtieTool |
| ArtieCLI | https://github.com/ArtieBots/ArtieCLI |
| ArtieWorkbench | https://github.com/ArtieBots/ArtieWorkbench |
| ArtieDaemons | https://github.com/ArtieBots/ArtieDaemons |
| Artie00 | https://github.com/ArtieBots/Artie00 |

Artie Tool resolves a component's version in this order:

1. a release manifest, if one is in force (see below)
2. the component's `VERSION` file
3. an exact git tag on `HEAD`, with a leading `v` stripped
4. the short git hash - what a development build gets

For example, a fix in ArDK bumps ArDK and nothing else.

## Images

An image is tagged with the version of the component it came from, not with a single
number for the whole build:

```
artie-base:0.1.0            # from ArDK
artie-api-server:0.1.0      # from ArDK
artie-cli:0.0.1             # from ArtieCLI
artie-eyebrow-driver:0.1.0  # from Artie00
```

`--docker-tag` overrides this and stamps every image in one run with the same tag. That
is for CI and one-off development builds, not for releases.

## Release Manifests

Because no single number describes an Artie, a **release manifest** records one
combination of component versions, the commit each was built from, and the image tags that
combination produces:

```yaml
apiVersion: v1
release: '2026.3'
generated: '2026-08-30T18:52:50+00:00'
components:
  ardk:
    version: 0.1.0
    commit: 50f4acb
    repository: https://github.com/ArtieBots/ArDK.git
  artie00:
    version: 0.1.0
    commit: 3820aa7
    repository: https://github.com/ArtieBots/Artie00.git
  # ...
images:
  artie-base: 0.1.0
  artie-api-server: 0.1.0
  artie-eyebrow-driver: 0.1.0
  artie-cli: 0.0.1
  # ...
```

This is the artifact to cite in a paper, to attach to an experiment's data, and to hand
someone who needs to reproduce a result. The `components` section says what the software
was; the `images` section is what a deployment actually pulls.

### Generating

Build and test a workspace, then record what you just verified:

```bash
artie-tool build all
artie-tool test all-unit
artie-tool release manifest --release 2026.3 --manifest-out artie-release.yaml
```

Artie Tool warns if a component's checkout is dirty, because then the recorded commit does
not describe what was actually built.

### Using

Pass it to any command. Every component is pinned to the version the manifest names,
regardless of what the checkouts say:

```bash
artie-tool build all   --release-file artie-release.yaml
artie-tool deploy artie --release-file artie-release.yaml
```

On deploy, the per-image tags from the manifest's `images` section are passed to Helm as
`imageTags.<image-name>`, so each workload pulls the right version.

## Helm charts

Chart values carry an `imageTags` map keyed by image name, matching the manifest's
`images` section exactly:

```yaml
imageTags:
  artie-api-server: 0.1.0
  artie-eyebrow-driver: 0.1.0
```

Anything not listed falls back to the single `imageTag` value, which keeps a hand-set
deployment working. Artie Tool fills `imageTags` in from a manifest at install time, so
you do not normally edit it.

## Choosing a version number

Use semantic versioning. The interesting question for Artie is what counts as a breaking
change, and it differs per component (this list is non-exhaustive):

- **ArDK** - the library APIs and the wire protocols. A change to the CAN protocol, the
  RPC schema, or a library's public interface is breaking. The base image's contents are
  part of this contract too, since drivers build on it.
- **ArtieTool** - the task definition format, the workspace configuration, and the command
  line. A task definition that stops loading is breaking.
- **ArtieCLI** - the command line and its output formats, which the test suites parse.
- **Artie00** - the hardware manifest schema and the deployed workload names. New
  hardware revisions are the usual reason to bump it.

When components must change together - a protocol change in ArDK that drivers in Artie00
have to follow - release them together and record the pair in a manifest.
