"""
Module for the Controller Module's Yocto image.
"""
from . import common
from . import container_eyebrows_driver
from . import container_mouth_driver
import logging
import os
import shutil
import subprocess
import sys

YOCTO_CONTROLLER_MODULE_BUILD_TASK_NAME = "yocto-controller-module"

def _build_cm_yocto(args) -> common.BuildResult:
    """
    Build the Yocto image for Controller Module.
    """
    common.set_up_logging(args)
    logging.info("Building Yocto image for controller module...")

    # Check if we are on Linux. If not, there's no point in continuing.
    if sys.platform != "linux":
        e = OSError("Invalid OS for Yocto build. Only Linux is supported.")
        return common.BuildResult(name=YOCTO_CONTROLLER_MODULE_BUILD_TASK_NAME, success=False, error=e)

    # Git clone artie-controller-node
    git_repo_location = os.path.join(common.repo_root(), "artie-controller-node")
    subprocess.run("git clone https://github.com/MaxStrange/artie-controller-node.git", cwd=git_repo_location).check_returncode()

    # Run the setup script
    subprocess.run("./setup.sh", shell=True, cwd=git_repo_location).check_returncode()

    # Source the environment and run bit-bake
    yocto_image = args.controller_module_yocto_image
    subprocess.run(f'source ./poky/oe-init-build-env "$PWD"/build && bitbake {yocto_image}', shell=True, cwd=git_repo_location)

    # Create the SD card image
    subprocess.run("./create-img.sh", shell=True, cwd=git_repo_location)

    # Yocto binary is found here
    yocto_binary_fpath = os.path.join(git_repo_location, "pi.img")

    return common.BuildResult(
        name=YOCTO_CONTROLLER_MODULE_BUILD_TASK_NAME,
        success=True,
        error=None,
        artifacts={
            common.ArtifactTypes.YOCTO_IMAGE: yocto_binary_fpath
        }
    )

def _clean_cm_yocto(args):
    """
    Clean up after ourselves.
    """
    common.clean_build_stuff()

    # Clean up the artie-controller-node git repository
    git_repo_location = os.path.join(common.repo_root(), "artie-controller-node")
    if os.path.exists(git_repo_location):
        shutil.rmtree(git_repo_location, ignore_errors=True)

# Remember to use 'yocto-' for all Yocto items
BUILD_CHOICES = set([
    common.BuildTask(
        name=YOCTO_CONTROLLER_MODULE_BUILD_TASK_NAME,
        build_function=_build_cm_yocto,
        artifacts=set([
            common.ArtifactTypes.YOCTO_IMAGE
        ]),
        dependencies={
            container_mouth_driver.MOUTH_DRIVER_BUILD_TASK_NAME: [common.ArtifactTypes.DOCKER_IMAGE],
            container_eyebrows_driver.EYEBROW_DRIVER_BUILD_TASK_NAME: [common.ArtifactTypes.DOCKER_IMAGE],
        },
        clean_function=_clean_cm_yocto
    ),
])
