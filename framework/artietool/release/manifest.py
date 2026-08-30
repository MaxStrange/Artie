"""
Release manifests.

Artie's components version independently, so no single number says what an Artie *is*.
A release manifest closes that gap: it records one combination of component versions,
along with the exact commit each was built from, and the image tags that combination
produces. It is the thing to cite in a paper, to pin a deployment to, and to hand
someone who needs to reproduce a result.

Generate one from a workspace that has just built and tested successfully:

    artie-tool release manifest --release 2026.3 --manifest-out artie-release.yaml

and use it later to build or deploy exactly that combination:

    artie-tool --release-file artie-release.yaml deploy artie
"""
from .. import common
from .. import workspace
from ..build import build
import argparse
import datetime
import os

import yaml

MANIFEST_API_VERSION = "v1"


def _image_names_by_component() -> dict:
    """
    Map each component to the base names of the Docker images its build tasks produce.
    """
    images = {}
    for task in build.build_tasks():
        for job in task.jobs:
            base_name = getattr(job, "img_base_name", None)
            if base_name:
                images.setdefault(task.repo, set()).add(base_name)

    return {repo: sorted(names) for repo, names in images.items() if repo}


def generate(args) -> int:
    """
    Write a release manifest describing the current state of the workspace.
    """
    cfg = workspace.config(args)
    images_by_component = _image_names_by_component()

    components = {}
    images = {}
    for name in workspace.known_repo_names():
        status = workspace.repo_status(name, cfg)
        if not status["exists"]:
            common.warning(f"{name}: no checkout at {status['path']}, leaving it out of the manifest")
            continue

        if status["dirty"]:
            common.warning(f"{name}: checkout is dirty - the recorded commit does not describe what is actually there")

        version = workspace.component_version(name)
        components[name] = {
            "version": version,
            "commit": status["head"],
            "repository": cfg.repo(name).url,
        }

        for base_name in images_by_component.get(name, []):
            images[base_name] = version

    manifest = {
        "apiVersion": MANIFEST_API_VERSION,
        "release": args.release,
        "generated": datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat(),
        "components": components,
        # Flattened for convenience: this is what a Helm chart needs, so that nothing has
        # to re-derive which component produced which image.
        "images": images,
    }

    text = yaml.safe_dump(manifest, sort_keys=False, default_flow_style=False)
    if args.manifest_out:
        with open(args.manifest_out, "w", encoding="utf-8") as f:
            f.write(text)
        common.info(f"Wrote release manifest '{args.release}' to {os.path.abspath(args.manifest_out)}")
    else:
        print(text)

    return 0


def fill_subparser(parser_manifest: argparse.ArgumentParser, parent: argparse.ArgumentParser):
    parser_manifest.add_argument("--release", default=None, type=str, help="A name for this combination of component versions, for example '2026.3'. Defaults to the current date.")
    parser_manifest.add_argument("--manifest-out", default=None, type=str, help="Write the manifest to this path instead of to stdout.")
    parser_manifest.set_defaults(cmd=_generate_with_default_name, module="release-manifest")


def _generate_with_default_name(args) -> int:
    if not args.release:
        args.release = datetime.date.today().isoformat()
    return generate(args)
