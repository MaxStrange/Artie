from typing import List
from .. import common
from . import artifact
from . import job
from . import result
import os
import shutil
import subprocess
import sys

class YoctoBuildJob(job.Job):
    def __init__(self, artifacts: List[artifact.Artifact], repo: str, script: str, binary_fname: str) -> None:
        super().__init__(artifacts)
        self.repo = repo
        self.script = script
        self.binary_fname = binary_fname
        self.git_repo_location = os.path.join(common.repo_root(), common.get_random_dirname())

    def __call__(self, args) -> result.JobResult:
        common.info("Building Yocto image for controller module...")

        # Check if we are on Linux. If not, there's no point in continuing.
        if sys.platform != "linux":
            e = OSError("Invalid OS for Yocto build. Only Linux is supported.")
            return result.JobResult(name=self.name, success=False, error=e)

        # Git clone artie-controller-node
        os.makedirs(self.git_repo_location)
        subprocess.run(f"git clone {self.repo} -o repo", cwd=git_repo_location).check_returncode()
        inside_git_repo = os.path.join(git_repo_location, "repo")

        # Run the build job's script
        script_fpath = os.path.join(inside_git_repo, "temp-script-for-build-job.sh")
        with open(script_fpath, 'w') as f:
            f.write(self.script)
        subprocess.run(f"chmod +x ./{script_fpath} && ./{script_fpath}", cwd=inside_git_repo).check_returncode()

        # Yocto binary is found here; copy it to artifacts folder
        yocto_binary_fpath = os.path.join(inside_git_repo, self.binary_fname)
        shutil.copyfile(yocto_binary_fpath, self._get_binary_fpath(args))

        # Fill in the artifacts
        self.mark_all_artifacts_as_built()

        return result.JobResult(self.name, success=True, artifacts=self.artifacts)

    def clean(self, args):
        super().clean(args)
        if os.path.exists(self.git_repo_location):
            shutil.rmtree(self.git_repo_location, ignore_errors=True)
