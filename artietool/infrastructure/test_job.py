from typing import Dict
from typing import List
from . import artifact
from . import dependency
from . import job
from . import result
from .. import common
from .. import docker
from enum import Enum
from enum import unique
import datetime
import logging
import time
import traceback

@unique
class TestStatuses(Enum):
    """
    These are the allowable status values for a test result.
    """
    SUCCESS = 0
    FAIL = 1
    DID_NOT_RUN = 2

class ExpectedOutput:
    """
    An `ExpectedOutput` is a string that we expect to find inside a Docker container.
    """
    def __init__(self, what: str, where: str | dependency.Dependency, cli=False) -> None:
        self.what = what
        self.where = where
        self.cli = cli  # is 'where' the CLI container? It gets treated differently than all the others
        self.pid = None  # Needs to be filled in by whoever launches the DUT(s)

    def evaluated_where(self, args) -> str:
        """
        Returns our `where`, after evaluating it if it is a dependency.
        """
        if issubclass(type(self.where), dependency.Dependency):
            where = self.where.evaluate(args).item
        else:
            where = self.where
        return where

    def check(self, args, test_name: str, task_name: str, timeout_s: float) -> result.TestResult|None:
        """
        Return whether the what can be found in the where. Ignores requests to check for CLI containers.
        """
        if self.cli:
            return None

        logging.info(f"Checking {test_name}'s DUT(s) for output...")
        container = docker.get_container(self.pid)
        if container is None:
            return result.TestResult(test_name, producing_task_name=task_name, status=result.TestStatuses.FAIL, msg=f"Could not find container corresponding to {self.evaluated_where(args)}")

        timestamp = datetime.datetime.now().timestamp()
        try:
            logging.info(f"Reading logs from {container.name} to find '{self.what}'...")
            for line in container.logs(stream=True, follow=True):
                if args.docker_logs:
                    logging.info(line.decode())

                if self.what in line.decode():
                    return result.TestResult(test_name, producing_task_name=task_name, status=result.TestStatuses.SUCCESS)

                if datetime.datetime.now().timestamp() - timestamp > timeout_s:
                    return result.TestResult(test_name, producing_task_name=task_name, status=TestStatuses.FAIL, exception=TimeoutError(f"Timeout waiting for '{self.what}' in {self.evaluated_where(args)}"))
        except docker.docker_errors.NotFound:
            return result.TestResult(test_name, producing_task_name=task_name, status=TestStatuses.FAIL, msg=f"Container closed unexpectedly while reading its logs.")

        return result.TestResult(test_name, producing_task_name=task_name, status=TestStatuses.FAIL, msg=f"Container exited while we were waiting for '{self.what}' in {self.evaluated_where(args)}")

    def check_in_logs(self, args, logs: str, test_name: str, task_name: str) -> result.TestResult:
        """
        Same as check, but uses logs to do the checking, instead of the where and is typically used for CLI containers.
        """
        logging.info(f"Checking {test_name}'s DUT(s) for output in logs...")
        if self.what in logs:
            return result.TestResult(test_name, task_name, result.TestStatuses.SUCCESS)
        else:
            return result.TestResult(test_name, task_name, result.TestStatuses.FAIL)

class CLITest:
    def __init__(self, test_name: str, cli_image: str, cmd_to_run_in_cli: str, expected_outputs: List[ExpectedOutput]) -> None:
        self.test_name = test_name
        self.cli_image = cli_image
        self.cmd_to_run_in_cli = cmd_to_run_in_cli
        self.expected_outputs = expected_outputs
        self.producing_task_name = None  # Filled in by Job

    def __call__(self, args) -> result.TestResult:
        # Launch the CLI command
        res = self._run_cli(args)
        if res.status != result.TestStatuses.SUCCESS:
            return res

        # Check the DUT(s) output(s)
        results = self._check_duts(args)
        results = [r for r in results if r is not None and r.status != result.TestStatuses.SUCCESS]

        # If we got more than one result, let's log the various problems and just return the first failing one
        if len(results) > 1:
            logging.error(f"Multiple failures detected in {self.test_name}. Returning the first detected failure and logging all of them.")

        for r in results:
            logging.error(f"Error in test {self.test_name}: {r.to_verbose_str()}")

        if results:
            return results[0]

        return result.TestResult(self.test_name, producing_task_name=self.producing_task_name, status=TestStatuses.SUCCESS)

    def link_pids_to_expected_outs(self, args, pids: Dict[str, str]):
        """
        Link each of this test's ExpectedOutput objects to its actual pid.
        """
        for e in self.expected_outputs:
            where = e.evaluated_where(args)
            if where in pids:
                e.pid = pids[e.evaluated_where(args)]
            else:
                raise KeyError(f"Cannot find a Docker ID corresponding to a Docker container that is expected to be running in this test. Offending container: {where}; available PIDs: {pids}")

    def _evaluated_cli_image(self, args) -> str:
        """
        Returns self.cli_image after evaluating it if it is a Dependency.
        """
        if issubclass(type(self.cli_image), dependency.Dependency):
            cli_img = self.cli_image.evaluate(args).item
        else:
            cli_img = docker.construct_docker_image_name(args, self.cli_image)
        return cli_img

    def _find_expected_cli_out(self, args) -> ExpectedOutput|None:
        """
        Attempt to find the CLI output from the ExpectedOutputs and return it.
        """
        for ex in self.expected_outputs:
            if ex.cli:
                return ex
        return None

    def _run_cli(self, args) -> result.TestResult:
        """
        Run a single CLI command and check it for expected_cli_out.

        Return None if success or a failing TestResult otherwise.
        """
        logs = self._try_ntimes(args, 3)

        expected_cli_out = self._find_expected_cli_out(args)
        if expected_cli_out is not None:
            return expected_cli_out.check_in_logs(args, logs, self.test_name, self.producing_task_name)
        else:
            # We do not expect anything interesting from CLI logs
            return result.TestResult(self.test_name, self.producing_task_name, result.TestStatuses.SUCCESS)

    def _try_ntimes(self, args, n: int):
        """
        Try running the CLI command up to `n` times to guard against transient timing errors. Yuck.
        """
        cli_img = self._evaluated_cli_image(args)
        kwargs = {'network_mode': 'host'}
        for i in range(n):
            try:
                logs = docker.run_docker_container(cli_img, self.cmd_to_run_in_cli, timeout_s=args.test_timeout_s, log_to_stdout=args.docker_logs, **kwargs)
                return logs
            except Exception:
                if i != n - 1:
                    logging.warning(f"Got an exception while trying to run CLI. Will try {n - (i+1)} more times.")
                    time.sleep(1)
                else:
                    raise

    def _check_duts(self, args) -> List[result.TestResult]:
        """
        Runs _check_dut() on each DUT pid, managing the total test timeout appropriately.
        """
        timeout_s = args.test_timeout_s
        results = []
        for expected_out in self.expected_outputs:
            r = expected_out.check(args, self.test_name, self.producing_task_name, timeout_s)
            if r is not None and r.exception is not None and type(r.exception) == TimeoutError:
                timeout_s = 1  # Give us a chance to collect the rest of the results
            results.append(r)
        return results

class TestJob(job.Job):
    """
    All TestJobs run a setup(), then a bunch of steps, then a teardown().
    Each step should be a single test that returns a test result.
    """

    def __init__(self, artifacts: List[artifact.Artifact], steps: List[callable]) -> None:
        super().__init__(artifacts)
        self.steps = steps

    def __call__(self, args) -> result.JobResult:
        self.setup(args)
        results = self._run_steps(args)
        self.teardown(args)

        # Check success
        success = True
        for r in results:
            if r.status == TestStatuses.FAIL:
                success = False
                break

        self.mark_all_artifacts_as_built()
        return result.JobResult(self.name, success=success, artifacts=results)

    def _run_steps(self, args) -> List[result.TestResult]:
        """
        Run each test in this job and return the list of results.
        """
        results = []
        for i, t in enumerate(self.steps):
            try:
                test_result = common.manage_timeout(t, args.test_timeout_s, args)
                results.append(test_result)
            except Exception as e:
                # Log exception if --enable-error-tracing
                if args.enable_error_tracing:
                    logging.error(f"Error running test {t.test_name}: {''.join(traceback.format_exception(e))}")
                else:
                    logging.error(f"Test {t.test_name} failed due to an exception ({e})")

                # Add this result
                results.append(result.TestResult(t.test_name, producing_task_name=self.parent_task.name, status=TestStatuses.FAIL, exception=e))

                # Mark all remaining tests as DID_NOT_RUN if user is not using --force-completion
                if args.force_completion:
                    logging.info("--force-completion argument detected. Running rest of tests in this task.")
                elif not args.force_completion and i + 1 < len(self.steps):
                    logging.info("Marking rest of this task's tests as DID_NOT_RUN. Use --force-completion flag to change this behavior.")
                    for remaining_test in self.steps[i+1:]:
                        results.append(result.TestResult(remaining_test.test_name, producing_task_name=self.parent_task.name, status=TestStatuses.DID_NOT_RUN))
                    return results
                else:
                    logging.info(f"Finished test: {t.test_name}")
                    return results
        return results

    def link(self, parent, index: int):
        super().link(parent, index)
        for s in self.steps:
            s.producing_task_name = parent.name

    def setup(self, args):
        """
        Set up for all the tests we will run in this task.
        """
        pass

    def teardown(self, args):
        """
        Clean up after ourselves. Should be overridden by the subclass.
        """
        pass
