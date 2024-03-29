from typing import Dict
from typing import List
from . import dependency
from . import test_job
from .. import common
from .. import docker
import time

class SingleContainerCLISuiteJob(test_job.TestJob):
    def __init__(self, steps: List[test_job.CLITest], docker_image_under_test: str | dependency.Dependency, cmd_to_run_in_dut: str, dut_port_mappings: Dict[int, int]) -> None:
        super().__init__(artifacts=[], steps=steps)
        self.dut = docker_image_under_test
        self.cmd_to_run_in_dut = cmd_to_run_in_dut
        self.dut_port_mappings = dut_port_mappings
        self._dut_container = None

    def setup(self, args):
        """
        Set up the DUT by using this object's `docker_cmd`.
        """
        super().setup(args)
        if issubclass(type(self.dut), dependency.Dependency):
            docker_image_name = self.dut.evaluate(args).item
        else:
            docker_image_name = str(docker.construct_docker_image_name(args, self.dut, common.host_platform()))

        kwargs = {'environment': {'ARTIE_RUN_MODE': 'unit'}, 'ports': self.dut_port_mappings}
        self._dut_container = docker.start_docker_container(docker_image_name, self.cmd_to_run_in_dut, **kwargs)
        for step in self.steps:
            step.link_pids_to_expected_outs(args, {docker_image_name: self._dut_container.id})

        # Give some time for the container to initialize before we start testing it
        common.info("Waiting for DUT to come online...")
        time.sleep(min(args.test_timeout_s / 3, 10))

    def teardown(self, args):
        """
        Shutdown any Docker containers still at large.
        """
        if args.skip_teardown:
            common.info(f"--skip-teardown detected. You will need to manually clean up the Docker containers.")
            return

        super().teardown(args)
        common.info(f"Tearing down. Stopping docker container...")
        try:
            self._dut_container.stop()
        except docker.docker_errors.NotFound:
            pass  # Container already stopped
