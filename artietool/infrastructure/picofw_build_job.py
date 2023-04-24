from . import artifact
from . import dependency
from . import docker_build_job
from . import result
from .. import common
from .. import docker
from typing import List
import logging
import os
import shutil

class PicoFWBuildJob(docker_build_job.DockerBuildJob):
    def __init__(self, artifacts: List[artifact.Artifact], img_base_name: str, dockerfile_dpath: str, fw_files_in_container: List[str], buildx=False, dockerfile="Dockerfile", build_context=".", dependency_files:List[dependency.Dependency | str]=None, build_args: List[docker_build_job.DockerBuildArg] = None) -> None:
        super().__init__(artifacts, img_base_name, dockerfile_dpath, buildx, dockerfile, build_context, dependency_files, build_args)
        self.fw_fpaths_in_container = fw_files_in_container

    def __call__(self, args) -> result.JobResult:
        # Build the Docker image
        super().__call__(args)

        # super() marked all of our artifacts, but we shouldn't mark any files yet
        for art in self.artifacts:
            if issubclass(type(art), artifact.FilesArtifact):
                art.built = False

        # super() should have produced exactly one Docker-Image type artifact
        docker_images_we_built = [art for art in self.artifacts if type(art) == artifact.DockerImageArtifact]
        if len(docker_images_we_built) != 1:
            msg = f"PicoFWBuildJob expects its parent DockerBuildJob to produce exactly one DockerImageArtifact, but we produced {len(docker_images_we_built)}"
            logging.error(msg)
            raise Exception(msg)
        elif not docker_images_we_built[0].item:
            msg = f"PicoFWBuildJob expects its parent DockerBuildJob to produce a DockerImageArtifact, but for some reason the image we built has no name. Image: {docker_images_we_built[0].item}"
        docker_image_name = docker_images_we_built[0].item

        # Run the Docker image and copy its files out
        logging.info(f"Running a Docker container to retrieve FW files...")
        docker.docker_copy(docker_image_name, self.fw_fpaths_in_container, args.artifact_folder)

        # Rename the files to include the git tag
        fnames = [os.path.basename(fpath) for fpath in self.fw_fpaths_in_container]
        for fname in fnames:
            fpath = os.path.join(args.artifact_folder, fname)
            fname_no_ext, suf = os.path.splitext(fpath)
            target = os.path.join(args.artifact_folder, fname_no_ext) + "-" + common.git_tag() + suf
            if os.path.isfile(target):
                os.remove(target)
            shutil.move(fpath, target)

        # Now mark all artifacts
        self.mark_all_artifacts_as_built()

        return result.JobResult(self.name, success=True, artifacts=self.artifacts)

    def clean(self, args):
        super().clean(args)
