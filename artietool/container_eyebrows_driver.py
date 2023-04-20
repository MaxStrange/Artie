"""
Stuff pertaining to the eyebrows driver container.
"""
from . import common
from . import fw_eyebrows
import logging
import os
import shutil
import subprocess

EYEBROW_DRIVER_BUILD_TASK_NAME = "container-eyebrows"

def _build_eyebrows_driver(args) -> common.BuildResult:
    """
    Build the eyebrows driver container image.
    """
    common.set_up_logging(args)
    logging.info("Building eyebrow driver container image...")

    # Copy the Artie Libs into a tmp folder
    builddpath = os.path.join(common.repo_root(), "drivers", "mouth-and-eyebrows")
    tmpdpath = os.path.join(builddpath, "tmp")
    common.copy_artie_libs(tmpdpath)

    # Docker image name
    git_tag = common.git_tag() if args.docker_tag is None else args.docker_tag
    repo_prefix = "" if args.docker_repo is None else args.docker_repo + "/"
    docker_image_name = f"{repo_prefix}artie-eyebrow-driver:{git_tag}"
    logging.info(f"Building Docker image and tagging it as {docker_image_name}")

    # Retrieve dependencies
    fw_image = args._artifacts[fw_eyebrows.EYEBROW_BUILD_TASK_NAME][common.ArtifactTypes.DOCKER_IMAGE]
    logging.info(f"Using {fw_image} as the base Docker image for driver build.")

    # Build the Docker image
    dockerargs = f"--build-arg DRIVER_TYPE=eyebrows --build-arg FW_IMG={fw_image} --build-arg RPC_PORT=4242"
    dockercmd = f"docker buildx build --load --platform linux/arm64 -f Dockerfile {dockerargs} -t {docker_image_name} ."
    subprocess.run(dockercmd, cwd=builddpath).check_returncode()

    # Push the Docker image to the chosen repo (if given)
    if args.docker_repo is not None:
        logging.info(f"Pushing Docker image {docker_image_name}...")
        p = subprocess.run(f"docker push {docker_image_name}")
        p.check_returncode()

    return common.BuildResult(
        name=EYEBROW_DRIVER_BUILD_TASK_NAME,
        success=True,
        artifacts={
            common.ArtifactTypes.DOCKER_IMAGE: docker_image_name
        }
    )

def _clean_eyebrows_driver(args):
    """
    Clean up after ourselves.
    """
    common.clean_build_stuff()

    builddpath = os.path.join(common.repo_root(), "drivers", "mouth-and-eyebrows")
    tmpdpath = os.path.join(builddpath, "tmp")
    if os.path.isdir(tmpdpath):
        shutil.rmtree(tmpdpath)

BUILD_CHOICES = set([
    common.BuildTask(
        name=EYEBROW_DRIVER_BUILD_TASK_NAME,
        build_function=_build_eyebrows_driver,
        artifacts=set([
            common.ArtifactTypes.DOCKER_IMAGE,
        ]),
        dependencies={
            "fw-eyebrows": [common.ArtifactTypes.DOCKER_IMAGE],
        },
        clean_function=_clean_eyebrows_driver
    ),
])
