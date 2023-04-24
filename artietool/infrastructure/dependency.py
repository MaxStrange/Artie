from . import artifact
from typing import List
import re

class Dependency:
    """
    A Dependency between tasks.
    """
    def __init__(self, producing_task_name: str, artifact_name: str, matchexpr:str=None) -> None:
        self.producing_task_name = producing_task_name
        self.artifact_name = artifact_name
        self.matchexpr = matchexpr
        if self.matchexpr:
            try:
                _ = re.compile(self.matchexpr)
            except Exception as e:
                raise ValueError(f"Malformed regular expression match pattern: {self.matchexpr}")

    def evaluate(self, args) -> artifact.Artifact | List[str]:
        """
        Uses `args` to find the artifact this dependency points to, then returns it.

        If we have a matchexpr, we will use it on the artifact's items to find
        all matching items and return them as a list of str.
        """
        art = artifact.retrieve_artifact(args, self.producing_task_name, self.artifact_name)
        if not self.matchexpr:
            return art

        ret = []
        pattern = re.compile(self.matchexpr)
        for i in art.item:
            if pattern.match(i):
                ret.append(i)
        return ret
