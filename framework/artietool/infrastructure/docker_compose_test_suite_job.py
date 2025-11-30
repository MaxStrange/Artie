from typing import List
from typing import Tuple
from . import dependency
from . import test_job
from .. import common
from .. import docker
import os

class DockerComposeTestSuiteJob(test_job.TestJob):
    def __init__(self, steps: List[test_job.CLITest], compose_fname: str, compose_docker_image_variables: List[Tuple[str, str|dependency.Dependency]], docker_network_name: str) -> None:
        super().__init__(artifacts=[], steps=steps)
        self.compose_fname = compose_fname
        self.compose_variables = compose_docker_image_variables  # List of (key, value) pairs; gets transformed into dict[str: str] when setup() is called
        self.compose_dpath = os.path.join(common.repo_root(), "framework", "artietool", "compose-files")
        self.docker_network_name = docker_network_name
        self.project_name = os.path.splitext(self.compose_fname)[0].replace('.', '-')
        self._dut_pids = {}

    def _set_compose_variables(self, args):
        compose_variables = {}
        for k, v in self.compose_variables:
            if issubclass(type(v), dependency.Dependency):
                compose_variables[k] = v.evaluate(args).item
            else:
                compose_variables[k] = v
        self.compose_variables = compose_variables

    def setup(self, args):
        """
        Set up the DUTs by using Docker compose.
        """
        super().setup(args)
        if not os.path.isdir(self.compose_dpath):
            raise FileNotFoundError(f"Cannot find compose-files directory at {self.compose_dpath}")

        docker.add_network(self.docker_network_name)
        self._set_compose_variables(args)
        self._dut_pids = docker.compose(self.project_name, self.compose_dpath, self.compose_fname, args.test_timeout_s, envs=self.compose_variables)
        for step in self.steps:
            step.link_pids_to_expected_outs(args, self._dut_pids)

    def teardown(self, args):
        """
        Shutdown any Docker containers still at large.
        """
        if args.skip_teardown:
            common.info(f"--skip-teardown detected. You will need to manually clean up the Docker containers.")
            return

        super().teardown(args)
        common.info(f"Tearing down. Stopping docker containers...")
        docker.compose_down(self.project_name, self.compose_dpath, self.compose_fname, envs=self.compose_variables)
        docker.remove_network(self.docker_network_name)
