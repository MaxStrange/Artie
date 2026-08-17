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

    def _tag_locally(self, args, manifest_name: str):
        """
        Stand in for the manifest list when there is no registry to put one in.

        A manifest list only exists inside a registry, but downstream consumers (tests,
        deployments) refer to this artifact by its manifest name regardless. With no
        repo configured, nothing would ever produce that name, so the name resolves to
        nothing locally and Docker falls back to trying to pull it. Point the name at
        the arch-specific image that can actually run on this machine instead.
        """
        evaluated_images = self._evaluate_images(args, self.images)
        host_arch = docker.get_host_architecture()

        # Prefer an image built for this machine's architecture; it's the only one we could run.
        local_arches = {img: docker.get_local_image_architecture(img) for img in evaluated_images}
        runnable = [img for img, arch in local_arches.items() if arch and arch == host_arch]
        if not runnable:
            # Nothing runnable here. Fall back to anything that at least exists locally.
            runnable = [img for img, arch in local_arches.items() if arch]

        if not runnable:
            common.warning(f"No docker repo specified and none of the images for manifest {manifest_name} were found locally ({evaluated_images}), so {manifest_name} will not resolve to anything. Anything that consumes it will try to pull it and fail.")
            return

        source = runnable[0]
        common.info(f"No docker repo specified, so there is nowhere to put a manifest list. Tagging {source} as {manifest_name} locally instead (host architecture: {host_arch or 'unknown'}).")
        docker.tag_docker_image(source, manifest_name)

    def __call__(self, args) -> result.JobResult:
        if args.docker_repo is None:
            manifest_name = str(docker.construct_docker_image_name(args, self.img_base_name))
            self._tag_locally(args, manifest_name)
            self.mark_all_artifacts_as_built()
            return result.JobResult(self.name, success=True, artifacts=self.artifacts)

        if getattr(args, 'platforms', None):
            common.info("A --platforms filter is active, so not all architectures may have been built. Skipping docker manifest creation; run again without --platforms to assemble manifests.")
            return result.JobResult(self.name, success=True, artifacts=self.artifacts)

        common.info(f"Creating docker manifest...")

        # Turn all the images we need into real images from dependencies
        evaluated_images = self._evaluate_images(args, self.images)

        manifest_name = str(docker.construct_docker_image_name(args, self.img_base_name))

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
