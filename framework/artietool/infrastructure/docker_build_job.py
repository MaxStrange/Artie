from . import artifact
from . import dependency
from . import job
from . import result
from .. import common
from .. import docker
from typing import List
import glob
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
    def __init__(self, artifacts: List[artifact.Artifact], img_base_name: str, dockerfile_dpath: str, buildx=False, dockerfile="Dockerfile", build_context=".", dependency_files:List[dependency.Dependency | str]=None, build_args:List[DockerBuildArg]=None, platform=None) -> None:
        super().__init__(artifacts)
        self.img_base_name = img_base_name
        self.dockerfile_dpath = dockerfile_dpath
        self.buildx = buildx
        self.dockerfile_fname = dockerfile
        self.build_context = build_context
        self.dependency_fpaths = dependency_files if dependency_files else []
        self.build_args = build_args if build_args else []
        self.platform = platform

    def __call__(self, args) -> result.JobResult:
        platform = self.platform if self.platform else ("linux/arm64" if self.buildx else "linux/amd64")
        platforms_filter = getattr(args, 'platforms', None)

        if getattr(args, 'manifests_only', False):
            common.info(f"--manifests-only given: not building {self.img_base_name} for {platform}. Assuming it has already been built and pushed.")
            self.mark_all_artifacts_as_built()
            return result.JobResult(self.name, success=True, artifacts=self.artifacts)

        if platforms_filter and platform.split('/')[-1] not in [p.split('/')[-1] for p in platforms_filter]:
            # Mark the artifact as built (by name) rather than pulling it: another job/machine is
            # responsible for this platform, and pulling a foreign-arch image here would be a large
            # download that nothing on this machine can run anyway.
            common.info(f"Skipping build of {self.img_base_name} for {platform}: not in --platforms {platforms_filter}. Assuming another build produced it.")
            self.mark_all_artifacts_as_built()
            return result.JobResult(self.name, success=True, artifacts=self.artifacts)

        if self.artifacts and all(art.built for art in self.artifacts) and not args.force_build:
            common.info(f"All artifacts of {self.img_base_name} for {platform} are already built or cached. Skipping this build job.")
            return result.JobResult(self.name, success=True, artifacts=self.artifacts)

        common.info(f"Building {self.img_base_name}...")

        # Grab all the dependency file locations
        fpaths = []
        for dep in self.dependency_fpaths:
            if issubclass(type(dep), dependency.Dependency):
                items = dep.evaluate(args)
            else:
                items = dep

            if issubclass(type(items), list):
                for item in items:
                    fpaths.extend(glob.glob(item))
            else:
                fpaths.extend(glob.glob(items))
        common.info(f"Found {fpaths} to copy into Docker context")

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
                    common.error(msg)
                    raise Exception(msg)
                else:
                    fpath = value[0]
                    buildargs += f" --build-arg {arg.key}={os.path.basename(fpath)}"


        # Create the name object from the Docker repo, name, and tag
        docker_image_name = docker.construct_docker_image_name(args, self.img_base_name, self.platform, repo=getattr(self.parent_task, 'repo', None))

        # If --force, we have to remove the image first
        if args.force_build:
            docker.remove_docker_image(docker_image_name, fail_ok=True)

        # Build the Docker image
        docker.build_docker_image(args, self.dockerfile_dpath, docker_image_name, self.buildx, fpaths, self.build_context, buildargs, self.dockerfile_fname, platform=self.platform)

        self.mark_all_artifacts_as_built()

        return result.JobResult(self.name, success=True, artifacts=self.artifacts)

    def clean(self, args):
        docker.clean_build_location(args, self.dockerfile_dpath)
