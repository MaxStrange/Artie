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
        if args.docker_repo is None:
            common.info("No docker repo specified. Skipping docker manifest creation.")
            self.mark_all_artifacts_as_built()
            return result.JobResult(self.name, success=True, artifacts=self.artifacts)

        if getattr(args, 'platforms', None):
            common.info("A --platforms filter is active, so not all architectures may have been built. Skipping docker manifest creation; run again without --platforms to assemble manifests.")
            return result.JobResult(self.name, success=True, artifacts=self.artifacts)

        common.info(f"Creating docker manifest...")

        # Turn all the images we need into real images from dependencies
        evaluated_images = self._evaluate_images(args, self.images)

        manifest_name = str(docker.construct_docker_image_name(args, self.img_base_name, repo=getattr(self.parent_task, 'repo', None)))

        if args.insecure_docker_repo:
            # 'buildx imagetools' has no --insecure support, so use the legacy manifest flow here.
            common.info(f"Removing manifest named {manifest_name} if it exists locally...")
            docker.remove_manifest(manifest_name, fail_ok=True)

            common.info(f"Creating manifest named {manifest_name}...")
            manifest = docker.create_manifest(manifest_name, evaluated_images, insecure=True)

            common.info(f"Annotating manifest {manifest_name}...")
            docker.annotate_manifest(manifest_name, evaluated_images)

            common.info(f"Pushing manifest {manifest_name}...")
            docker.push_manifest(manifest)
        else:
            common.info(f"Creating and pushing manifest {manifest_name}...")
            docker.create_and_push_manifest_via_imagetools(manifest_name, evaluated_images)

        self.mark_all_artifacts_as_built()
        return result.JobResult(self.name, success=True, artifacts=self.artifacts)

    def clean(self, args):
        super().clean(args)
