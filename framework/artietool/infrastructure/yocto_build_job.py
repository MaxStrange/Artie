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

        if not hasattr(args, 'yocto_hosts') or args.yocto_hosts is None:
            args.yocto_hosts = {}
        else:
            args.yocto_hosts = self._parse_yocto_hosts(args.yocto_hosts)

        if not hasattr(args, 'yocto_insecure_registries') or args.yocto_insecure_registries is None:
            args.yocto_insecure_registries = []
        else:
            args.yocto_insecure_registries = args.yocto_insecure_registries.split(',')

        # Now that we have runtime arguments, we can replace variables in places that need it
        self.binary_fname = common.replace_vars_in_string(self.binary_fname, args)
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
            current_branch = subprocess.run(["git", "branch", "--show-current"], cwd=git_repo_location, capture_output=True, text=True, check=True).stdout.strip()
            if current_branch != args.repo_branch:
                e = ValueError(f"Existing repo at {git_repo_location} is on branch '{current_branch}', but expected branch '{args.repo_branch}' Backing off to avoid potentially overwriting data.")
                return result.JobResult(name=self.name, success=False, error=e)
        else:
            common.info(f"Cloning repo {self.repo} (branch {args.repo_branch}) into {git_repo_location}...")
            subprocess.run([f"git", "clone", self.repo, "-b", args.repo_branch, git_repo_location]).check_returncode()

        # Now, clone all the layers
        for layer in self.layers:
            if os.path.exists(os.path.join(git_repo_location, layer.name)) and args.skip_clone:
                common.info(f"Yocto layer {layer.name} already exists at {git_repo_location}/{layer.name}, skipping clone.")
                continue
            layer_path = os.path.join(git_repo_location, layer.name)
            common.info(f"Cloning Yocto layer {layer.name} from {layer.url} into {layer_path}...")
            # Clone the layer
            cmd = [f"git", "clone", layer.url, layer_path]
            subprocess.run(cmd).check_returncode()
            # Checkout the tag if specified
            if layer.tag is not None:
                common.info(f"Checking out tag {layer.tag} for layer {layer.name}...")
                subprocess.run([f"git", "checkout", "-t", f"origin/{layer.tag}"], cwd=layer_path).check_returncode()
            # Now create our own branch for modifications
            subprocess.run([f"git", "checkout", "-b", f"{layer.tag}-local"], cwd=layer_path).check_returncode()

        # Run the setup script
        common.info(f"Running Yocto setup script...")
        setup_result = self.setup_script.run_script(args, cwd=git_repo_location, args=["--insecure-registries", ','.join(args.yocto_insecure_registries), "--hosts", ','.join([f"{addr}  {host}" for addr, host in args.yocto_hosts.items()])])
        if not setup_result.returncode == 0:
            return result.JobResult(name=self.name, success=False, error=OSError(f"Yocto setup script failed with return code {setup_result.returncode}. Stdout: {setup_result.stdout}; Stderr: {setup_result.stderr}."))

        # Run the build command
        common.info(f"Running Yocto build command...")
        build_result = self.build_cmd.run_script(args, cwd=git_repo_location)
        if not build_result.returncode == 0:
            return result.JobResult(name=self.name, success=False, error=OSError(f"Yocto build command failed with return code {build_result.returncode}. Stdout: {build_result.stdout}; Stderr: {build_result.stderr}."))

        # Run the post-build script
        common.info(f"Running Yocto post-build script...")
        post_result = self.post_script.run_script(args, cwd=git_repo_location)
        if not post_result.returncode == 0:
            return result.JobResult(name=self.name, success=False, error=OSError(f"Yocto post-build script failed with return code {post_result.returncode}. Stdout: {post_result.stdout}; Stderr: {post_result.stderr}."))

        # Copy the built binary to the artifacts directory
        built_binary_path = os.path.join(git_repo_location, self.binary_fname)
        shutil.copy(built_binary_path, os.path.join(common.default_build_location(), self.binary_fname))

        # Fill in the artifacts
        self.mark_all_artifacts_as_built()

        return result.JobResult(self.name, success=True, artifacts=self.artifacts)

    def clean(self, args):
        super().clean(args)

    def _parse_yocto_hosts(self, s: str) -> dict[str, str]:
        """
        Parse the given string `s` into a dictionary of the form
        address: host name.

        `s` should be a comma-separated list of items of the form address:host.
        """
        hosts = {}

        items = s.split(',')
        for item in items:
            parts = item.split(':')
            if len(parts) != 2:
                raise ValueError(f"Invalid yocto host specification: {item}. Expected format is address:host.")
            address, host = parts
            hosts[address] = host

        return hosts
