import uuid

from . import dependency
from . import result
from . import test_job
from .. import common
from .. import docker


class PytestTest:
    """Represents a single pytest test suite execution."""

    def __init__(self, test_name: str, expected_outputs: list[test_job.ExpectedOutput]=None, unexpected_outputs: list[test_job.UnexpectedOutput]=None) -> None:
        self.test_name = test_name
        self.expected_outputs = expected_outputs or []
        self.unexpected_outputs = unexpected_outputs or []
        self.stop_event = False
        self.producing_task_name = None  # Filled in by Job

        if not expected_outputs and not unexpected_outputs:
            raise ValueError(f"Test {test_name} has no expected outputs or unexpected outputs. At least one of them is required.")

    def __call__(self, args) -> result.TestResult:
        """The test setup has already run the Pytest suite. Now we just collect this test's results."""
        try:
            # Check the DUT(s) output(s)
            common.debug(f"Checking DUT(s) for expected outputs for test {self.test_name}...")
            results = self._check_duts(args)
            results = [r for r in results if r is not None and r.status != result.TestStatuses.SUCCESS]

            # If we got more than one result, let's log the various problems and just return the first failing one
            if len(results) > 1:
                common.error(f"Multiple failures detected in {self.test_name}. Returning the first detected failure and logging all of them.")

            for r in results:
                common.error(f"Error in test {self.test_name}: {r.to_verbose_str()}")

            if results:
                return results[0]

            return result.TestResult(self.test_name, producing_task_name=self.producing_task_name, status=test_job.TestStatuses.SUCCESS)

        except Exception as e:
            common.error(f"Exception while running test {self.test_name}: {e}")
            return result.TestResult(self.test_name, producing_task_name=self.producing_task_name, status=test_job.TestStatuses.FAIL, exception=e)

    def link_pids_to_expected_outs(self, args, pids: dict[str, str]):
        """
        Link each of this test's ExpectedOutput objects to its actual pid.
        """
        for e in self.expected_outputs:
            where = e.evaluated_where(args)
            if where in pids:
                e.pid = pids[e.evaluated_where(args)]
            else:
                raise KeyError(f"Cannot find a Docker ID corresponding to a Docker container that is expected to be running in this test. Offending container: {where}; available PIDs: {pids}")

        for u in self.unexpected_outputs:
            where = u.evaluated_where(args)
            if where in pids:
                u.pid = pids[u.evaluated_where(args)]
            else:
                raise KeyError(f"Cannot find a Docker ID corresponding to a Docker container that is expected to be running in this test. Offending container: {where}; available PIDs: {pids}")

    def _check_duts(self, args) -> list[result.TestResult]:
        """
        Runs _check_dut() on each DUT pid, managing the total test timeout appropriately.

        Short-circuits at the first unexpected output, so results may not be equal
        in length to the sum of expected and unexpected outputs.
        """
        timeout_s = args.test_timeout_s
        results = []

        for unexpected_out in self.unexpected_outputs:
            r = unexpected_out.check(args, self.test_name, self.producing_task_name, timeout_s, follow=False, stream=False)
            if r is not None and r.exception is not None and type(r.exception) == TimeoutError:
                timeout_s = 1  # Give us a chance to collect the rest of the results

            # Check for short circuit
            if r is not None and r.status != result.TestStatuses.SUCCESS:
                results.append(r)
                return results

            results.append(r)

        for expected_out in self.expected_outputs:
            r = expected_out.check(args, self.test_name, self.producing_task_name, timeout_s, follow=False, stream=False)
            if r is not None and r.exception is not None and type(r.exception) == TimeoutError:
                timeout_s = 1  # Give us a chance to collect the rest of the results
            results.append(r)

        return results

class SingleContainerPytestSuiteJob(test_job.TestJob):
    """
    Job that runs pytest test suites inside a single container.

    This job type is designed for Python projects with pytest-based unit tests.
    It runs the entire test suite in one container and reports the results.

    The DUT gets a freshly created Docker network to itself, rather than the default bridge that
    every container shares. A suite that talks over the network to itself - the Artie CAN suites
    simulate a CAN bus over UDP multicast, for instance - is otherwise audible to every other
    container on the host, so two runs at once become one shared bus and corrupt each other's
    traffic. That reads as a failing test with nothing wrong with it. Isolating the DUT means two
    jobs on one machine, or a developer running a suite while CI runs, cannot interfere.

    The flip side is that a suite run by this job cannot reach anything outside its own container.
    That suits a unit-test suite, which is what this job is for; a suite that needs to talk to
    another container wants the docker-compose job instead.
    """

    def __init__(self, steps: list[PytestTest], docker_image_under_test: str | dependency.Dependency, cmd_to_run_in_dut: str|None) -> None:
        super().__init__(artifacts=[], steps=steps)
        self.dut = docker_image_under_test
        self.cmd_to_run_in_dut = cmd_to_run_in_dut
        self._dut_container = None
        self._network_name = None

    def setup(self, args):
        """
        Set up the DUT by using this object's `docker_cmd`.
        """
        super().setup(args)
        if issubclass(type(self.dut), dependency.Dependency):
            docker_image_name = self.dut.evaluate(args).item
        else:
            docker_image_name = str(docker.construct_docker_image_name(args, self.dut, common.host_platform()))

        # A random name rather than one derived from the task, because the whole point is that two
        # runs of the same task on one host stay apart - and add_network() refuses a name that is
        # already taken, so a fixed name would turn a collision into a hard failure instead.
        self._network_name = f"artie-pytest-{uuid.uuid4().hex[:12]}"
        common.info(f"Creating an isolated Docker network for the DUT: {self._network_name}")
        docker.add_network(self._network_name)

        kwargs = {'environment': {'ARTIE_RUN_MODE': 'unit'}, 'network': self._network_name}
        try:
            self._dut_container = docker.start_docker_container(docker_image_name, self.cmd_to_run_in_dut, remove=False, **kwargs)
        except Exception:
            # teardown() does not run if setup() raises, so the network would be left behind.
            docker.remove_network(self._network_name)
            self._network_name = None
            raise

        for step in self.steps:
            step.link_pids_to_expected_outs(args, {docker_image_name: self._dut_container.id})

        # The whole suite runs inside the DUT, and we check each test's result by scraping the
        # DUT's logs afterwards, so we need to let the suite run to completion before we start.
        common.info("Waiting for the test suite to finish running inside the DUT...")
        if not docker.wait_for_container_to_exit(self._dut_container, args.test_timeout_s):
            common.warning(f"DUT is still running after {args.test_timeout_s}s. Checking whatever output it has produced so far; if tests fail spuriously, try raising --test-timeout-s.")

    def teardown(self, args, results: list[result.TestResult]):
        """
        Shutdown any Docker containers still at large, and remove the DUT's network.
        """
        if args.skip_teardown:
            common.info(f"--skip-teardown detected. You will need to manually clean up the Docker container and the network {self._network_name}.")
            return

        super().teardown(args, results)
        common.info(f"Tearing down. Stopping (and removing) docker container...")
        try:
            # The network is removed in the finally block rather than after this: a container that
            # cannot be stopped or removed would otherwise leave its network behind too, and those
            # accumulate silently until something runs out of address space. remove_network() stops
            # whatever is still attached, so it copes with the container outliving this.
            if self._dut_container is not None:
                try:
                    self._dut_container.stop()
                except docker.docker_errors.NotFound:
                    common.info(f"Container not found. Possibly it has already stopped.")
                    pass  # Container already stopped

                try:
                    self._dut_container.remove()
                except docker.docker_errors.NotFound:
                    pass
        finally:
            if self._network_name is not None:
                try:
                    docker.remove_network(self._network_name)
                except Exception as e:
                    common.error(f"Could not remove Docker network {self._network_name}; you may need to clean it up by hand: {e}")
                self._network_name = None
