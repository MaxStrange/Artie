from typing import List
from . import test_job
from .. import common

class HardwareTestJob(test_job.TestJob):
    def __init__(self, steps: List[test_job.CLITest]) -> None:
        super().__init__(artifacts=[], steps=steps)

    def setup(self, args):
        """
        """
        super().setup(args)

    def teardown(self, args):
        """
        """
        if args.skip_teardown:
            common.info(f"--skip-teardown detected. You will need to manually clean up the Docker containers.")
            return

        super().teardown(args)
