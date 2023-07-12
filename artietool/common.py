"""
Common stuff for Artie Tool modules.
"""
import logging
import os
import random
import shutil
import string
import subprocess
import threading

try:
    from docker import errors as docker_errors
except ModuleNotFoundError:
    logging.error("'docker' not installed. Make sure to install dependencies with 'pip install -r requirements.txt'")
    exit(1)

class Colors:
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

class PropagatingThread(threading.Thread):
    """
    A Thread subclass that can properly handle exceptions.
    Taken from Stack Overflow: https://stackoverflow.com/questions/2829329/catch-a-threads-exception-in-the-caller-thread
    """
    def run(self):
        self.exc = None
        try:
            self.ret = self._target(*self._args, **self._kwargs)
        except BaseException as e:
            self.exc = e

    def join(self, timeout=None):
        super().join(timeout)
        if self.exc:
            raise self.exc

        if hasattr(self, 'ret'):
            return self.ret
        else:
            return None

def register_task(choices):
    """
    Decorator to add a Task to the given list, for registering with argparse.
    """
    def decorator(cls):
        instantiated_task = cls()
        choices.append(instantiated_task)
        logging.debug(f"Registered {instantiated_task.name} task with argparse choices")
        return cls
    return decorator

def clean_tmp(builddpath: str):
    """
    Removes the 'tmp' directory if there is one under the given `builddpath`.
    """
    tmpdpath = os.path.join(builddpath, "tmp")
    if os.path.isdir(tmpdpath):
        shutil.rmtree(tmpdpath)

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

    # Clean the random scratch location
    scratch = os.path.join(repo_root(), "tmp")
    if os.path.isdir(scratch):
        shutil.rmtree(scratch)

def copy_artie_libs(dest):
    """
    Copy all the Artie Libraries into the given folder.
    """
    libpath = os.path.join(repo_root(), "libraries")
    libs = [os.path.join(libpath, d) for d in os.listdir(libpath) if os.path.isdir(os.path.join(libpath, d)) and d != "base-image"]
    for lib in libs:
        destpath = os.path.join(dest, os.path.basename(lib))
        if not os.path.exists(destpath):
            logging.info(f"Trying to copy {lib} to {destpath}")
            try:
                shutil.copytree(lib, destpath)
            except FileExistsError:
                # Race condition - someone beat us to it
                pass

def default_build_location():
    """
    Get the default build location.
    """
    return os.path.join(repo_root(), "build-artifacts")

def default_test_results_location():
    """
    Get the default test results location.
    """
    return os.path.join(repo_root(), "test-results")

def get_random_dirname() -> str:
    """
    Get a random string suitable for a temporary directory.
    """
    return "tempdir-" + "".join(random.choices(string.ascii_letters, k=8))

def get_task_modules():
    """
    Get the file names (without .py) of all the task modules for dynamic import.
    """
    task_folder = os.path.join(repo_root(), "artietool", "tasks")
    return [os.path.splitext(fname)[0] for fname in os.listdir(task_folder) if os.path.splitext(fname)[-1] == ".py"]

def find_task_from_name(name: str, tasks):
    """
    Finds and retrieves the Task from the tasks list based on its name.

    Returns None if can't find it.
    """
    for t in tasks:
        if t.name == name:
            return t
    return None

def get_scratch_location():
    """
    Return a location we can use for scratch stuff.
    """
    scratch_location = os.path.join(repo_root(), "tmp")
    if not os.path.isdir(scratch_location):
        os.makedirs(scratch_location, exist_ok=True)  # Hopefully nip any race conditions in the bud

    return scratch_location

def git_tag() -> str:
    """
    Return the git tag of the Artie repo.
    """
    p = subprocess.run("git log --format='%h' -n 1".split(' '), capture_output=True)
    p.check_returncode()
    return p.stdout.decode('utf-8').strip().strip("'")

def manage_timeout(func, timeout_s: int, *args, **kwargs):
    """
    Runs `func` with `args` and `kwargs` to completion, or until `timeout_s` seconds
    has elapsed, at which point it raises a TimeoutError.
    """
    class TimeoutWrapper:
        def __init__(self, func, timeout_s) -> None:
            self.func = func
            self.timeout_s = timeout_s
            self.ret = None

        def __call__(self, *args, **kwargs):
            try:
                self.ret = self.func(*args, **kwargs)
            except docker_errors.ContainerError as e:
                # Docker exceptions are not pickleable and so can't be propagated across the
                # test task boundary into the infrastructure module. It just hangs if you try.
                raise Exception(f"Container failed to start: {e}")

    wrapper = TimeoutWrapper(func, timeout_s)
    t = PropagatingThread(target=wrapper, args=args, kwargs=kwargs, daemon=True)
    t.start()
    t.join(timeout=timeout_s)
    if t.is_alive():
        if hasattr(func, 'name'):
            name = func.name
        elif hasattr(func, 'test_name'):
            name = func.test_name
        elif hasattr(func, '__name__'):
            name = func.__name__
        else:
            name = type(func)
        raise TimeoutError(f"Trying to run function {name} failed with a timeout.")
    return wrapper.ret

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
    if not hasattr(args, "loglevel"):
        setattr(args, "loglevel", "info")
    logging.basicConfig(format=format, level=getattr(logging, args.loglevel.upper()), force=True)
