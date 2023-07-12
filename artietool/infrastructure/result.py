from . import artifact
from .. import common
from typing import List
import enum
import os
import traceback

@enum.unique
class TestStatuses(enum.Enum):
    """
    These are the allowable status values for a test result.
    """
    SUCCESS = 0
    FAIL = 1
    DID_NOT_RUN = 2

class TestResult:
    def __init__(self, name, producing_task_name=None, status=None, exception=None, msg=None):
        self.name = name
        self.producing_task_name = producing_task_name
        self.status = status if status is not None else TestStatuses.SUCCESS
        self.exception = exception
        self.msg = msg

    def __repr__(self) -> str:
        return f"{self.name} result: {self.status}"

    def __str__(self) -> str:
        return self.__repr__()

    def __hash__(self) -> int:
        return hash(f"{self.producing_task_name}.{self.name}")

    @property
    def item(self):
        return str(self)

    def to_verbose_str(self) -> str:
        """
        Create a verbose string from this result, suitable for logging to a file.
        """
        s  = f"=============================" + os.linesep
        s += f"{self.name}" + os.linesep
        s += f"=============================" + os.linesep
        s += f"Status: {self.status}" + os.linesep
        s += f"Task: {self.producing_task_name}" + os.linesep
        if self.msg:
            s += self.msg + os.linesep
        if self.exception:
            s += os.linesep.join(traceback.format_exception(self.exception))
        return s

class JobResult:
    def __init__(self, name: str, success: bool, error:Exception=None, artifacts:List[artifact.Artifact]=None) -> None:
        """
        The result of a job.

        - name: The name of the Job.
        - success: Did we successfully run the task? If not, `error` should be given.
        - error: If we got an error while running, this is that error/exception. May be a list of errors in the case of multiple failures.
        - artifacts: If given, should be a list of Artifact objects.
        """
        self.name = name
        self.success = success
        self.error = error
        self.artifacts = artifacts

    def __str__(self):
        """
        Returns a summary of this Result.
        """
        status = f"{common.Colors.OKGREEN}OK{common.Colors.ENDC}" if self.success else f"{common.Colors.FAIL}FAIL{common.Colors.ENDC}"
        s =  f"{self.name}: [{status}]:"
        s += self._common_str()
        return s

    def _common_str(self) -> str:
        s = ""
        if self.artifacts is not None:
            s += os.linesep + "    Build Artifacts:"
            for art in self.artifacts:
                s += os.linesep + f"        {art.name}: {art.item}"
        if self.error:
            s += os.linesep + "    Error: " + str(self.error)
        return s

    def to_verbose_str(self) -> str:
        """
        Returns a verbose string, with self.error expanded into a traceback, if applicable.
        Does not use colors, as this is meant for logging to a file.
        """
        status = "OK" if self.success else "FAIL"
        s = f"{self.name}: [{status}]"
        s += self._common_str()
        if self.error:
            s += os.linesep + "The following exception occurred in this task:"
            s += os.linesep
            s += os.linesep.join(traceback.format_exception(self.error))
        return s

class TaskResult:
    def __init__(self, name: str, job_results: List[JobResult|TestResult]):
        """
        The result of a task.

        Args
        ----
        - name: The name of the task item, for logging and printing. Not necessarily a path to a build artifact.
        """
        self.name = name
        self.job_results = job_results
        self.success = True
        for r in self.job_results:
            if hasattr(r, 'success') and not r.success:
                self.success = False
            elif hasattr(r, 'status') and r.status == TestStatuses.FAIL:
                self.success = False

    def __str__(self) -> str:
        s = ""
        s += f"{self.name}:"
        for j in self.job_results:
            s += os.linesep + f"{j}"
        return s

    def to_verbose_str(self) -> str:
        s = ""
        s += f"{self.name}:"
        for j in self.job_results:
            s += os.linesep + f"{j.to_verbose_str()}"
        return s

    def get_artifacts(self) -> List[artifact.Artifact]:
        ret = []
        for j in self.job_results:
            ret.extend(j.artifacts)
        return ret

class ErrorTaskResult:
    def __init__(self, name: str, error: Exception) -> None:
        """
        The result of running a task when that task fails catastrophically, and fails to return a result itself.
        """
        self.name = name
        self.error = error
        self.success = False
        self.job_results = []

    def __str__(self):
        """
        Returns a summary of this Result.
        """
        status = f"{common.Colors.FAIL}FAIL{common.Colors.ENDC}"
        s =  f"{self.name}: [{status}]:"
        s += self._common_str()
        return s

    def _common_str(self) -> str:
        s = ""
        if self.error:
            s += os.linesep + "    Error: " + str(self.error)
        return s

    def to_verbose_str(self) -> str:
        """
        Returns a verbose string, with self.error expanded into a traceback, if applicable.
        Does not use colors, as this is meant for logging to a file.
        """
        status = "FAIL"
        s = f"{self.name}: [{status}]"
        s += self._common_str()
        s += os.linesep + "The following exception occurred in this task:"
        s += os.linesep
        s += os.linesep.join(traceback.format_exception(self.error))
        return s

    def get_artifacts(self):
        return []
