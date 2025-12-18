from . import artifact
from .. import common
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
    DRIVER = 'driver'               # A task that builds/tests a driver

    STRESS = 'stress'               # A stress test
    UNIT = 'unit'                   # A unit test
    INTEGRATION = 'integration'     # An integration test
    SANITY = 'sanity'               # A sanity check
    HARDWARE = 'hardware'           # A test to be run on hardware

    CONTAINER_SET = 'container-set' # A Helm deployment or similar


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
        results = []
        for j in self.jobs:
            r = j(args)
            artifact.add_artifacts_from_result(args, r)
            results.append(r)
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
            if cliarg.action is not None:
                task_parser.add_argument(cliarg.name, default=cliarg.default_val, help=cliarg.arg_help, action=cliarg.action)
            else:
                task_parser.add_argument(cliarg.name, default=cliarg.default_val, choices=cliarg.choices, help=cliarg.arg_help, type=cliarg.arg_type)

    def fill_artifacts_at_runtime(self, args):
        """
        Fill the artifacts' values, now that we have all the information we need (task configuration and command line args).
        """
        for j in self.jobs:
            common.info(f"Filling in {j}'s artifacts from task {self}...")
            j.fill_artifacts_at_runtime(args)

    def mark_if_cached(self, args):
        """
        Mark each artifact as built if it can be found on disk.
        """
        for j in self.jobs:
            common.info(f"Checking if {self}'s {j} is cached...")
            j.mark_if_cached(args)

    def _link_jobs(self):
        """
        Go through each Job and initialize it with our self as parent and give our artifacts
        as pointers for the Job to fill in.
        """
        for i, j in enumerate(self.jobs):
            j.link(self, i)
            j.claim_artifacts()

class TestTask(Task):
    """
    A TestTask is a Task that runs one or more tests and is invoked by the CLI's 'test' module.
    """
    pass

class HardwareTestTask(TestTask):
    """
    A HardwareTestTask is a Task that runs on the actual Artie hardware. There's some nonsense
    associated with it to ensure that we only run exactly one HardwareTestTask and one
    hardware test job at a time.
    """
    def _collapse_all_hw_test_jobs(self, hw_test_jobs):
        # Smush them all together into the first one
        for j in hw_test_jobs[1:]:
            hw_test_jobs[0].combine(j)

        # Now remove them all but the first one
        return [hw_test_jobs[0]]

    def combine(self, other) -> None:
        """
        Combines this test task with another one. The other one is left unchanged.
        """
        if not issubclass(type(other), HardwareTestTask):
            # Can't combine with a non-HardwareTestTask
            return

        # First of all, I should only have at most one hardware test job. Otherwise I need to collapse
        # them into each other on my own object before I can combine them on another one.
        common.info(f"Combining {self.name} with {other.name}")
        self.name = "HW-Tests"
        hw_test_jobs = [j for j in self.jobs if hasattr(j, 'is_hw_test_job') and j.is_hw_test_job]
        if len(hw_test_jobs) == 0:
            # This is odd. How are we a HardwareTestTask if we don't have any HardwareTestJobs?
            raise ValueError(f"Misconfigured HardwareTestTask: no hardware test jobs associated with it.")
        elif len(hw_test_jobs) > 1:
            hw_test_jobs = self._collapse_all_hw_test_jobs(hw_test_jobs)

        # We should now have exactly one hw_test_job
        hw_test_job = hw_test_jobs[0]

        # Next, that one hardware test job (if it exists) should gobble up ALL hardware test jobs
        # in the other task.
        for j in other.jobs:
            if hasattr(j, 'is_hw_test_job') and j.is_hw_test_job:
                hw_test_job.combine(j)

class DeployTask(Task):
    """
    A DeployTask is a Task that removes or adds a set of items such as containers to the workload.
    """
    pass

class BuildTask(Task):
    """
    A BuildTask is a Task that builds something and is invoked by the CLI's 'build' module.
    """
    pass
