"""
Flash Yocto Image Job
"""
from . import artifact
from . import dependency
from . import job
from . import result
from .. import common
import os
import sys
import subprocess

class FlashYoctoImageJob(job.Job):
    """
    A FlashYoctoImageJob flashes a Yocto image onto a specified device.
    """
    def __init__(self, image: dependency.Dependency|str) -> None:
        super().__init__([])  # Flash Yocto Image Job does not produce artifacts
        self.image = image  # Gets evaluated to a string path during execution

    def __call__(self, args):
        if not hasattr(args, 'device') or args.device is None:
            raise ValueError("Device path must be specified to flash the Yocto image.")

        # Check if we are on Linux. If not, there's no point in continuing.
        if sys.platform != "linux":
            common.error("Yocto flash jobs are only supported on Linux hosts.")
            e = OSError("Invalid OS for Yocto flash job. Only Linux is supported.")
            return result.JobResult(name=self.name, success=False, error=e)

        device_path = args.device  # Device path passed as an argument
        yocto_image_path = self.image.evaluate() if issubclass(type(self.image), dependency.Dependency) else self.image

        if not os.path.exists(yocto_image_path):
            raise FileNotFoundError(f"Yocto image not found at {yocto_image_path}")

        if not os.path.exists(device_path):
            raise FileNotFoundError(f"Device not found at {device_path}")

        common.info(f"Flashing Yocto image {yocto_image_path} to device {device_path}...")

        # Use dd command to flash the image
        try:
            subprocess.run(['sudo', 'dd', f'if={yocto_image_path}', f'of={device_path}', 'bs=4M', 'status=progress', 'conv=fsync'], check=True)
            common.info("Flashing completed successfully.")
            self.mark_all_artifacts_as_built()
            return result.JobResult(self.name, success=True, artifacts=self.artifacts)
        except subprocess.CalledProcessError as e:
            common.error(f"Flashing failed: {e}")
            return result.JobResult(self.name, success=False, artifacts=self.artifacts)
