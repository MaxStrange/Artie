from . import artifact
from . import dependency
from . import job
from . import result
from enum import StrEnum
from enum import unique
from typing import Any, List
import argparse

@unique
class Labels(StrEnum):
    """
    These are the available types of tests and build objects.
    """
    DOCKER_IMAGE = 'docker-image'   # A task that builds/tests a Docker image
    FIRMWARE = 'firmware'           # A task that builds/tests FW
    YOCTO = 'yocto'                 # A task that builds/tests a Yocto image
    BASE_IMAGE = 'base-image'       # A task that builds/tests a common base image
    TELEMETRY = 'telemetry'         # A task that builds/tests telemetry

    STRESS = 'stress'               # A stress test
    UNIT = 'unit'                   # A unit test
    INTEGRATION = 'integration'     # An integration test
    SANITY = 'sanity'               # A sanity check


class Task:
    """
    A Task is the basic unit of execution in Artie Tool and is composed of
    one or more Jobs, each of which produces 0 or more Artifacts.
    Tasks have Dependencies on other Tasks.

    Args
    ----
    - name: The name of the Task, which is used by other Tasks to reference this one as a Dependency.
    - labels: A list of Label enum values, which are useful for organizing the Task into groups of Tasks for the user to select at runtime.
    - dependencies: A list of Dependency objects, which explain how this Task depends on other ones.
    - artifacts: A list of Artifact objects, which define the types of things that this Task creates (if any).
    - cli_args: If given, we add these args to the CLI parsing machinery for the user to consume.
    """
    def __init__(self, name: str, labels: List[Labels], dependencies: List[dependency.Dependency], artifacts: List[artifact.Artifact], jobs: List[job.Job], cli_args=None) -> None:
        self.name = name
        self.labels = labels
        self.dependencies = dependencies
        self.artifacts = artifacts
        self.cli_args = cli_args
        self.jobs = jobs
        self._link_jobs()

    def __repr__(self) -> str:
        return self.name

    def __str__(self) -> str:
        return self.name

    def __call__(self, args) -> result.TaskResult:
        results = [j(args) for j in self.jobs]
        return result.TaskResult(self.name, results)

    def cached(self, args) -> bool:
        """
        Returns whether this Task is cached or not.
        """
        return all([art.built for art in self.artifacts])

    def clean(self, args):
        """
        Calls 'clean' on each job.
        """
        for j in self.jobs:
            j.clean(args)

    def fill_args_with_artifacts(self, args):
        """
        Fill out `args` with our artifacts.
        """
        for art in self.artifacts:
            artifact.add_artifact(args, art)

    def fill_subparser(self, task_parser: argparse.ArgumentParser, parent: argparse.ArgumentParser):
        if self.cli_args is None:
            return

        for cliarg in self.cli_args:
            task_parser.add_argument(cliarg.name, default=cliarg.default_val, choices=cliarg.choices, help=cliarg.arg_help)

    def fill_artifacts_at_runtime(self, args):
        """
        Fill the artifacts' values, now that we have all the information we need (task configuration and command line args).
        """
        for j in self.jobs:
            j.fill_artifacts_at_runtime(args)

    def mark_if_cached(self, args):
        """
        Mark each artifact as built if it can be found on disk.
        """
        for art in self.artifacts:
            art.mark_if_cached(args)

    def _link_jobs(self):
        """
        Go through each Job and initialize it with our self as parent and give our artifacts
        as pointers for the Job to fill in.
        """
        for i, j in enumerate(self.jobs):
            j.link(self, i)
            j.claim_artifacts()

class BuildTask(Task):
    """
    A BuildTask is a Task that builds something and is invoked by the CLI's 'build' module.
    """
    pass

class TestTask(Task):
    """
    A TestTask is a Task that runs one or more tests and is invoked by the CLI's 'test' module.
    """
    pass
