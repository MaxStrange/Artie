"""
Build module for the eyebrow MCU FW (both left and right).
"""
from . import common
import argparse
import logging
import os
import subprocess

EYEBROW_BUILD_TASK_NAME = "fw-eyebrows"

def _build_eyebrows(args) -> common.BuildResult:
    """
    Build the eyebrows FW.
    """
    common.set_up_logging(args)
    logging.info("Building eyebrow firmware...")

    # Set the location to the fw-eyebrow directory
    build_directory = os.path.abspath(os.path.join(common.repo_root(), "firmware", "eyebrows", "build"))
    logging.info(f"Building from {build_directory}")

    # Docker image name
    docker_image_name = common.construct_docker_image_name(args, "artie-eyebrows")
    logging.info(f"Building Docker image and tagging it as {docker_image_name}")

    # Build a Docker image
    p = subprocess.run(f"docker build -f Dockerfile -t {docker_image_name} ..", cwd=build_directory)
    p.check_returncode()

    # Push the Docker image to the chosen repo (if given)
    if args.docker_repo is not None:
        logging.info(f"Pushing Docker image {docker_image_name}...")
        p = subprocess.run(f"docker push {docker_image_name}")
        p.check_returncode()

    # Also run the Docker image as a container in one process, and in another process, copy the FW out
    logging.info(f"Running the Docker container to retrieve the FW files...")
    basename = "/pico/src/build/eyebrows"
    suffixes = [".elf", ".hex", ".bin", ".uf2"]
    common.docker_copy(docker_image_name, [basename + suf for suf in suffixes], args.artifact_folder)

    artifacts = {
        common.ArtifactTypes.DOCKER_IMAGE: docker_image_name,
        common.ArtifactTypes.FILES: [f"{args.artifact_folder}/eyebrows.{suffix}" for suffix in suffixes],
    }

    return common.BuildResult(
        name=EYEBROW_BUILD_TASK_NAME,
        success=True,
        artifacts=artifacts,
    )

def _clean_eyebrows(args):
    """
    Clean up after ourselves.
    """
    common.clean_build_stuff()

BUILD_CHOICES = set([
    common.BuildTask(
        name=EYEBROW_BUILD_TASK_NAME,
        build_function=_build_eyebrows,
        artifacts=set([
            common.ArtifactTypes.DOCKER_IMAGE,
            common.ArtifactTypes.FILES
        ]),
        dependencies=None,
        clean_function=_clean_eyebrows
    ),
])
