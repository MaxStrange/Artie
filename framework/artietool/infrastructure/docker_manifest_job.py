from . import artifact
from . import dependency
from . import job
from . import result
from .. import common
from .. import docker
from typing import List
import glob
import os

class DockerManifestJob(job.Job):
    """
    A DockerManifestJob creates and pushes a Docker manifest list (a multi-arch image).
    """
    def __init__(self, artifacts: List[artifact.Artifact], images: List[dependency.Dependency | str], image_base_name: str) -> None:
        super().__init__(artifacts)
        self.images = images
        self.img_base_name = image_base_name

    def _evaluate_images(self, args, images: List[str|dependency.Dependency]) -> List[str]:
        evaluated_images = []
        for img in images:
            if issubclass(type(img), dependency.Dependency):
                item = str(img.evaluate(args).item)
                evaluated_images.append(item)
            else:
                evaluated_images.append(img)
        return evaluated_images

    def __call__(self, args) -> result.JobResult:
        common.info(f"Creating docker manifest...")

        # Turn all the images we need into real images from dependencies
        evaluated_images = self._evaluate_images(args, self.images)

        manifest_name = str(docker.construct_docker_image_name(args, self.img_base_name))

        common.info(f"Removing manifest named {manifest_name} if it exists locally...")
        docker.remove_manifest(manifest_name, fail_ok=True)

        common.info(f"Creating manifest named {manifest_name}...")
        insecure = args.insecure_docker_repo
        manifest = docker.create_manifest(manifest_name, evaluated_images, insecure=insecure)

        common.info(f"Pushing manifest {manifest_name}...")
        docker.push_manifest(manifest)

        self.mark_all_artifacts_as_built()
        return result.JobResult(self.name, success=True, artifacts=self.artifacts)

    def clean(self, args):
        super().clean(args)
