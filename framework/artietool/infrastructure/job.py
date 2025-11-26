from .. import common
from . import artifact
from . import result
from typing import List
import abc

class Job(abc.ABC):
    """
    A Job is a sub-task. Tasks are composed of one or more Jobs, which
    are run sequentially within that Task.
    """
    def __init__(self, artifacts: List[artifact.Artifact]) -> None:
        self.artifacts = artifacts
        self.parent_task = None  # Filled in by Task.link()
        self.name = None         # Filled in by Task.link()

    @abc.abstractmethod
    def __call__(self, args) -> result.JobResult:
        pass

    def __str__(self) -> str:
        return self.name if self.name else "'Job name not known'"

    def claim_artifacts(self):
        """
        Copy the Artifact references that this Job is responsible for from the parent_task,
        overwriting the Artifacts that this Job was given at constructor time.
        """
        parent_artifacts = []
        for a in self.parent_task.artifacts:
            for b in self.artifacts:
                if a == b:
                    parent_artifacts.append(a)
        self.artifacts = parent_artifacts

    def clean(self, args):
        """
        Clean up after ourselves. Should be overridden by
        subclass if we need to clean up more than the default
        stuff.
        """
        common.clean_build_stuff()

    def fill_artifacts_at_runtime(self, args):
        """
        Fill in all of our artifacts based on configuration and args.
        """
        for art in self.artifacts:
            art.fill_item(args, self)

    def link(self, parent, index: int):
        """
        Link this job to the parent task, and link any sub-stuff to this job (by overriding this method).
        """
        self.parent_task = parent
        self.name = f"Job {index}"

    def mark_all_artifacts_as_built(self):
        """
        Mark each Artifact this Job produces as 'built'.
        """
        for art in self.artifacts:
            art.built = True

    def mark_if_cached(self, args):
        """
        Mark each artifact as built if it can be found on disk.
        """
        for art in self.artifacts:
            art.mark_if_cached(args)
