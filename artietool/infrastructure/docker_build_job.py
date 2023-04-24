from . import artifact
from . import dependency
from . import job
from . import result
from .. import docker
from typing import List
import logging
import os

class DockerBuildArg:
    def __init__(self, key: str, value: str | dependency.Dependency) -> None:
        self.key = key
        self.value = value

class DockerBuildJob(job.Job):
    """
    A DockerBuildJob builds a single Docker image using
    the parameters given.
    """
    def __init__(self, artifacts: List[artifact.Artifact], img_base_name: str, dockerfile_dpath: str, buildx=False, dockerfile="Dockerfile", build_context=".", dependency_files:List[dependency.Dependency | str]=None, build_args:List[DockerBuildArg]=None) -> None:
        super().__init__(artifacts)
        self.img_base_name = img_base_name
        self.dockerfile_dpath = dockerfile_dpath
        self.buildx = buildx
        self.dockerfile_fname = dockerfile
        self.build_context = build_context
        self.dependency_fpaths = dependency_files if dependency_files else []
        self.build_args = build_args if build_args else []

    def __call__(self, args) -> result.JobResult:
        logging.info(f"Building {self.img_base_name}...")

        # Grab all the dependency file locations
        fpaths = []
        for dep in self.dependency_fpaths:
            if issubclass(type(dep), dependency.Dependency):
                fpaths.extend(dep.evaluate(args))
            else:
                fpaths.append(dep)
        logging.info(f"Found {fpaths} to copy into Docker context")

        # Grab all the Docker build args and format into a string for Docker
        buildargs = ""
        for arg in self.build_args:
            if not issubclass(type(arg.value), dependency.Dependency):
                buildargs += f" --build-arg {arg.key}={arg.value}"
            else:
                # Things are a little trickier if we have a dependency.
                # We might have a single artifact (which can be turned into a string)
                # or we might have a list of strings (file paths) - which should be
                # exactly one string long.
                value = arg.value.evaluate(args)
                if issubclass(type(value), artifact.Artifact):
                    item = os.path.basename(value.item) if os.path.exists(value.item) else value.item
                    buildargs += f" --build-arg {arg.key}={item}"
                elif len(value) != 1:
                    msg = f"Can't understand the dependency {arg.value}. It should give either an Artifact or a list of length 1 of file paths. But got: {value} after evaluating."
                    logging.error(msg)
                    raise Exception(msg)
                else:
                    fpath = value[0]
                    buildargs += f" --build-arg {arg.key}={os.path.basename(fpath)}"


        docker.build_docker_image(args, self.dockerfile_dpath, self.img_base_name, self.buildx, fpaths, self.build_context, buildargs, self.dockerfile_fname)

        self.mark_all_artifacts_as_built()

        return result.JobResult(self.name, success=True, artifacts=self.artifacts)

    def clean(self, args):
        docker.clean_build_location(args, self.dockerfile_dpath)
