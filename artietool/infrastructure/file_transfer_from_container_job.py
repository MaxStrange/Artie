from artietool.infrastructure import artifact
from . import artifact
from . import dependency
from . import job
from . import result
from .. import common
from .. import docker
from typing import List
import os
import shutil

class FileTransferFromContainerJob(job.Job):
    def __init__(self, artifacts: List[artifact.Artifact], image: dependency.Dependency|str, fw_files_in_container: List[str]) -> None:
        super().__init__(artifacts)
        self.image = image
        self.fw_fpaths_in_container = fw_files_in_container

    def _evaluate_docker_image(self, args) -> str:
        # If the Docker image is a dependency, we have to evaluate it
        if issubclass(type(self.image), dependency.Dependency):
            docker_image_name = self.image.evaluate(args).item
        else:
            docker_image_name = self.image
        return docker_image_name

    def _copy_out_files(self, args, docker_image_name: str):
        common.info(f"Running a Docker container from image {docker_image_name} to retrieve FW files...")
        docker.docker_copy(docker_image_name, self.fw_fpaths_in_container, args.artifact_folder)

        # Rename the files to include the tag of the Docker file that built them
        tag = docker.get_tag_from_name(docker_image_name)
        fnames = [os.path.basename(fpath) for fpath in self.fw_fpaths_in_container]
        for fname in fnames:
            fpath = os.path.join(args.artifact_folder, fname)
            fname_no_ext, suf = os.path.splitext(fpath)
            target = os.path.join(args.artifact_folder, fname_no_ext) + "-" + tag + suf
            if os.path.isfile(target):
                os.remove(target)
            shutil.move(fpath, target)

    def __call__(self, args) -> result.JobResult:
        # Run the Docker image and copy its files out
        docker_image_name = self._evaluate_docker_image(args)
        self._copy_out_files(args, docker_image_name)

        # Now mark all artifacts
        self.mark_all_artifacts_as_built()

        return result.JobResult(self.name, success=True, artifacts=self.artifacts)

    def clean(self, args):
        super().clean(args)

    def mark_if_cached(self, args):
        """
        Mark each artifact as built if it can be found on disk.

        Override parent's version: we need to check if the files can be found on
        disk. If they aren't found, we need to check if the container that produces
        them is cached. If it is, we can pull from the container, and then mark ourselvees
        as cached as well.
        """
        for art in self.artifacts:
            art.mark_if_cached(args)

        found_on_disk = all([art.built for art in self.artifacts])
        if found_on_disk:
            # All files found on disk. Nothing left to do. We are definitely cached and the artifacts have marked themselves.
            return

        # If we couldn't find the files on disk, we need to see if the files
        # are produced by a container that can be found.
        docker_image_name = self._evaluate_docker_image(args)
        if not docker.check_and_pull_if_docker_image_exists(args, docker_image_name):
            # The image does not exist/is not cached. We can't get the files out without building an image.
            # So we aren't cached and the artifacts have marked themselves.
            return

        # If we pulled the image or it exists locally, let's copy out the files.
        self._copy_out_files(args, docker_image_name)

        # Now remark the artifacts
        for art in self.artifacts:
            art.mark_if_cached(args)

        # Check that they are all accounted for, otherwise we've hit an odd error (possibly a misconfiguration of the job)
        found_on_disk = all([art.built for art in self.artifacts])
        if not found_on_disk:
            errmsg = f"Not all artifacts were accounted for after transferring them from the container. Expected artifacts: {self.artifacts}; Docker image we used to transfer files: {docker_image_name}; Job: {self}"
            common.error(errmsg)
            raise AssertionError(errmsg)
