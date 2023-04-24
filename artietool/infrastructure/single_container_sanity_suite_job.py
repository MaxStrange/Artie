from . import dependency
from . import result
from . import test_job
from .. import docker
from typing import List

class SanityTest:
    def __init__(self, test_name: str, docker_image_under_test: str | dependency.Dependency, cmd_to_run_in_dut: str) -> None:
        self.test_name = test_name
        self.docker_image_under_test = docker_image_under_test
        self.cmd_to_run_in_dut = cmd_to_run_in_dut
        self.producing_task_name = None  # Filled in by Job

    def __call__(self, args) -> result.TestResult:
        if issubclass(type(self.docker_image_under_test), dependency.Dependency):
            docker_image_name = self.docker_image_under_test.evaluate(args).item
        else:
            docker_image_name = docker.construct_docker_image_name(args, self.docker_image_under_test)

        kwargs = {'environment': {'ARTIE_RUN_MODE': 'sanity'}}
        docker.run_docker_container(docker_image_name, self.cmd_to_run_in_dut, timeout_s=args.test_timeout_s, log_to_stdout=args.docker_logs, **kwargs)
        # If run_docker_container() doesn't raise an Exception, we have passed
        return result.TestResult(self.test_name, producing_task_name=self.producing_task_name, status=result.TestStatuses.SUCCESS)

class SingleContainerSanitySuiteJob(test_job.TestJob):
    def __init__(self, steps: List[SanityTest]) -> None:
        super().__init__(artifacts=[], steps=steps)
