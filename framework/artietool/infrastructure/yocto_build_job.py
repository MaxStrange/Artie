from typing import List
from .. import common
from . import artifact
from . import job
from . import result
from . import scriptdefs
import dataclasses
import os
import pathlib
import shutil
import subprocess
import sys

@dataclasses.dataclass
class YoctoLayer:
    """A layer in a Yocto build."""
    name: str
    url: str
    tag: str|None = None

class YoctoBuildJob(job.Job):
    def __init__(self, artifacts: List[artifact.Artifact], repo: str, repo_name: str, layers: List[YoctoLayer], setup_script: scriptdefs.ScriptDefinition, build_cmd: scriptdefs.ScriptDefinition, post_script: scriptdefs.ScriptDefinition, binary_fname: str) -> None:
        super().__init__(artifacts)
        self.repo = repo
        self.repo_name = repo_name
        self.layers = layers
        self.setup_script = setup_script
        self.build_cmd = build_cmd
        self.post_script = post_script
        self.binary_fname = binary_fname

    def __call__(self, args) -> result.JobResult:
        common.info("Building Yocto image for controller module...")

        # Check if we are on Linux. If not, there's no point in continuing.
        if sys.platform != "linux":
            common.error("Yocto builds are only supported on Linux hosts.")
            e = OSError("Invalid OS for Yocto build. Only Linux is supported.")
            return result.JobResult(name=self.name, success=False, error=e)

        # Put our args in order
        if not hasattr(args, 'yocto_image'):
            e = ValueError("Missing required argument '--yocto-image' for Yocto build job.")
            return result.JobResult(name=self.name, success=False, error=e)

        if not hasattr(args, 'skip_clone'):
            args.skip_clone = False

        if not hasattr(args, 'repos_directory') or args.repos_directory is None:
            args.repos_directory = '../'

        if not hasattr(args, 'repo_branch') or args.repo_branch is None:
            args.repo_branch = 'main'

        # Now that we have runtime arguments, we can replace variables in places that need it
        self.binary_fname = common.replace_variables(self.binary_fname, args)
        self.setup_script.fill_in_args(args)
        self.build_cmd.fill_in_args(args)
        self.post_script.fill_in_args(args)

        # Construct the proper repository location
        if pathlib.Path(args.repos_directory).is_absolute():
            git_repo_location = os.path.abspath(os.path.join(args.repos_directory, self.repo_name))
        else:
            git_repo_location = os.path.abspath(os.path.join(common.repo_root(), args.repos_directory, self.repo_name))

        # Check if the repo is already cloned. If so, we should error out to avoid overwriting anything,
        # unless '--skip-clone' is given.
        if os.path.exists(git_repo_location) and not args.skip_clone:
            e = FileExistsError(f"Yocto repo location {git_repo_location} already exists. Please remove it or use '--skip-clone' to skip cloning.")
            return result.JobResult(name=self.name, success=False, error=e)
        elif args.skip_clone and not os.path.exists(git_repo_location):
            e = FileNotFoundError(f"Cannot skip cloning because the repo location {git_repo_location} does not exist.")
            return result.JobResult(name=self.name, success=False, error=e)
        elif args.skip_clone and os.path.exists(git_repo_location):
            common.info(f"Skipping cloning of repo {self.repo} because '--skip-clone' was given and repository exists at {git_repo_location}.")
            common.info(f"Checking if the existing repo is on branch {args.repo_branch}...")
            current_branch = subprocess.run(f"git branch --show-current", cwd=git_repo_location, capture_output=True, text=True, check=True).stdout.strip()
            if current_branch != args.repo_branch:
                e = ValueError(f"Existing repo at {git_repo_location} is on branch '{current_branch}', but expected branch '{args.repo_branch}' Backing off to avoid potentially overwriting data.")
                return result.JobResult(name=self.name, success=False, error=e)
        else:
            common.info(f"Cloning repo {self.repo} (branch {args.repo_branch}) into {git_repo_location}...")
            subprocess.run(f"git clone {self.repo} -o {git_repo_location} -b {args.repo_branch}").check_returncode()

        # Now, clone all the layers
        for layer in self.layers:
            layer_path = os.path.join(git_repo_location, layer.name)
            common.info(f"Cloning Yocto layer {layer.name} from {layer.url} into {layer_path}...")
            cmd = f"git clone {layer.url} -o {layer_path}"
            if layer.tag is not None:
                cmd += f" -t {layer.tag} -b {layer.tag}-local"
            subprocess.run(cmd).check_returncode()

        # Run the setup script
        common.info(f"Running Yocto setup script...")
        setup_result = self.setup_script.run_script(cwd=git_repo_location, extra_args=[])
        if not setup_result.success:
            return result.JobResult(name=self.name, success=False, error=setup_result.error)
        
        # Run the build command
        common.info(f"Running Yocto build command...")
        build_result = self.build_cmd.run_script(cwd=git_repo_location, extra_args=[f"YOCTO_IMAGE={args.yocto_image}"])
        if not build_result.success:
            return result.JobResult(name=self.name, success=False, error=build_result.error)
        
        # Run the post-build script
        common.info(f"Running Yocto post-build script...")
        post_result = self.post_script.run_script(cwd=git_repo_location, extra_args=[f"image={args.yocto_image}"])
        if not post_result.success:
            return result.JobResult(name=self.name, success=False, error=post_result.error)

        # Fill in the artifacts
        self.mark_all_artifacts_as_built()

        return result.JobResult(self.name, success=True, artifacts=self.artifacts)

    def clean(self, args):
        super().clean(args)
