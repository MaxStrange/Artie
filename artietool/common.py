"""
Common stuff for Artie Tool modules.
"""
from enum import Enum, unique
import logging
import os
import random
import shutil
import string
import subprocess
import time

class Colors:
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

@unique
class ArtifactTypes(Enum):
    """
    These are the types of things that can be produced (and consumed) by BuildTasks.
    """
    DOCKER_IMAGE = 0  # A Docker image name
    FILES = 1         # A file path or list of file paths
    YOCTO_IMAGE = 2   # A Yocto image binary file path

class BuildTask:
    def __init__(self, name, build_function, artifacts, dependencies, clean_function) -> None:
        """
        A BuildTask is a single build function with associated build artifacts and dependencies.

        Args
        ----
        - name: A string name of the task. Should be unique across all tasks and must follow the convention
                that FW items start with fw-, container items start with container-, and yocto items start with yocto-.
        - build_function: The function to execute. It must take command line args as its only argument.
                          It can access dependencies from this argument like so: args._artifacts['task-name'][artifact].
                          These dependencies are added onto the args before it reaches the build function.
                          It should also return a BuildResult. Remember to set artifacts appropriately
                          (see `artifacts` below).
        - artifacts: A set of artifact identifiers (enum values). After the build function finishes, the
                     resulting BuildResult should contain a matching dict of artifacts, with keys being
                     the set of artifacts set in this object, and values being the actual artifacts themselves
                     as they would be used in subsequent build tasks (a path to a file or a Docker image name, etc.).
        - dependencies: A dict of k/v pairs, where the keys are the name of the BuildTask that generates the artifact
                        and the values are a list of artifact keys like this: {'fw-eyebrows': [ArtifactTypes.DOCKER_IMAGE, ArtifactTypes.FILES]}
        - clean_function: A function that should be used to clean up after ourselves. We run this exactly once per task
                          after all tasks have finished building, so while it does not need to be reintrant,
                          it should assume that any cleaning may have already been done by another, similar task.
                          This function should take `args` and return nothing.
        """
        valid_name = False
        valid_prefixes = ("fw-", "container-", "yocto-")
        for valid_prefix in valid_prefixes:
            if name.startswith(valid_prefix):
                valid_name = True
                break

        if not valid_name:
            raise ValueError(f"BuildTask name {name} is invalid. Must start with one of {valid_prefixes}")

        self.name = name
        self.build_function = build_function
        self.artifacts = artifacts
        self.dependencies = dependencies
        self.clean_function = clean_function

    def __str__(self):
        return self.name

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return self.name == other.name


class BuildResult:
    def __init__(self, name: str, success: bool, error=None, artifacts=None):
        """
        The result of an attempt to build an artifact.

        Args
        ----
        - name: The name of the artifact, for logging and printing. Not necessarily a path to a build artifact.
        - success: Did we successfully build the artifact? If not, `error` should be given.
        - error: If we got an error while building, this is that error/exception.
        - artifacts: If given, should be a dict of the form {'name': path or similar}
        """
        self.name = name
        self.success = success
        self.error = error
        self.artifacts = artifacts if artifacts is not None else {}

    def __str__(self):
        """
        Returns a summary of this BuildResult.
        """
        status = f"{Colors.OKGREEN}OK{Colors.ENDC}" if self.success else f"{Colors.FAIL}FAIL{Colors.ENDC}"
        s =  f"{self.name}: [{status}]:"
        if self.artifacts is not None:
            s += os.linesep + "    Build Artifacts:"
            for item, item_path in self.artifacts.items():
                s += os.linesep + f"        {item}: {item_path}"
        if self.error:
            s += os.linesep + "    Error: " + str(self.error)
        return s

def clean_build_stuff():
    """
    Clean up after ourselves as much as we can, not including the
    actual build artifacts.
    """
    # Check for a scratch location
    if os.path.isdir(get_scratch_location()):
        shutil.rmtree(get_scratch_location(), ignore_errors=True)

def clean():
    """
    Clean up after ourselves as much as we can, including artifacts.
    """
    clean_build_stuff()

    # Check for items in the default build folder
    for fname in os.listdir(default_build_location()):
        fpath = os.path.join(default_build_location(), fname)
        if os.path.isfile(fpath) and fname != ".gitkeep":
            os.remove(fpath)
        elif os.path.isdir(fpath):
            shutil.rmtree(fpath, ignore_errors=True)

def construct_docker_image_name(args, name, repo_prefix=None, tag=None) -> str:
    """
    Returns a string of the form "{repo_prefix}{name}:{tag}".

    `repo_prefix` defaults to "".
    `tag` defaults to git tag.
    """
    if tag is None:
        tag = git_tag() if args.docker_tag is None else args.docker_tag

    if repo_prefix is None:
        repo_prefix = "" if args.docker_repo is None else args.docker_repo + "/"

    return f"{repo_prefix}{name}:{tag}"

def copy_artie_libs(dest):
    """
    Copy all the Artie Libraries into the given folder.
    """
    libpath = os.path.join(repo_root(), "libraries")
    libs = [os.path.join(libpath, d) for d in os.listdir(libpath) if os.path.isdir(os.path.join(libpath, d))]
    for lib in libs:
        destpath = os.path.join(dest, os.path.basename(lib))
        if not os.path.exists(destpath):
            logging.info(f"Trying to copy {lib} to {destpath}")
            shutil.copytree(lib, destpath)

def default_build_location():
    """
    Get the default build location.
    """
    return os.path.join(repo_root(), "build-artifacts")

def docker_copy(image: str, paths_in_container: list, path_on_host: str):
    """
    Copy a given item or list of items from a Docker image onto the host.
    """
    scratch_location = get_scratch_location()
    if not os.path.isdir(scratch_location):
        os.makedirs(scratch_location, exist_ok=True)  # Hopefully nip any race conditions in the bud

    cidfile_fpath = os.path.join(scratch_location, f"_docker_id_{''.join(random.choices(string.ascii_letters, k=6))}.txt")
    p = subprocess.Popen(["docker", "run", "--rm", "--cidfile", cidfile_fpath, image], stdout=subprocess.DEVNULL)

    # Give it a moment to let the container start up
    time.sleep(1)

    # Get the docker ID
    docker_id = open(cidfile_fpath).read().strip()
    short_id = docker_id[:8]

    if not isinstance(paths_in_container, list):
        paths_in_container = [paths_in_container]

    # Do the actual copy
    for path in paths_in_container:
        logging.info(f"Copying {short_id}:{path} to {path_on_host}...")
        subprocess.run(f"docker cp {docker_id}:{path} {path_on_host}", stdout=subprocess.DEVNULL).check_returncode()

    # Stop the container
    logging.info(f"Sending stop signal to container {short_id}...")
    subprocess.run(f"docker stop {docker_id}", stdout=subprocess.DEVNULL).check_returncode()
    p.wait()

def get_scratch_location():
    """
    Return a location we can use for scratch stuff.
    """
    return os.path.join(repo_root(), "tmp")

def git_tag() -> str:
    """
    Return the git tag of the Artie repo.
    """
    p = subprocess.run("git log --format='%h' -n 1", capture_output=True)
    p.check_returncode()
    return p.stdout.decode('utf-8').strip().strip("'")

def repo_root() -> str:
    """
    Return the absolute path of the root of the Artie repository.
    """
    thisdir = os.path.dirname(os.path.abspath(__file__))
    root = os.path.join(thisdir, "..")
    if not os.path.isdir(root):
        raise FileNotFoundError("The Artie directory seems to have been altered in a way that I can't understand.")

    return os.path.abspath(root)

def set_up_logging(args):
    """
    Set up the logging for this process.
    """
    format = "[<%(asctime)s> %(processName)s (%(levelname)s)]: %(message)s"
    logging.basicConfig(format=format, level=getattr(logging, args.loglevel.upper()))
