"""
Common stuff for Artie Tool modules.
"""
from typing import Tuple
import argparse
import fabric
import invoke
import ipaddress
import logging
import os
import platform
import random
import re
import shutil
import socket
import string
import subprocess
import sys
import threading

from . import workspace

try:
    from docker import errors as docker_errors
except ModuleNotFoundError:
    logging.error("'docker' not installed. Make sure to install dependencies with 'pip install -r requirements.txt'")
    exit(1)

# The name of our logger
LOGGER_NAME = 'artietool'

# Matches ${REPO:<name>} in task definitions, resolving to another component's checkout.
_REPO_REF_PATTERN = re.compile(r"\$\{REPO:(?P<repo_name>[\w-]+)\}")

# Global list of threads that we have spawned and want to be able to kill if needed
_MANAGED_THREADS = []

class Colors:
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

class PropagatingThread(threading.Thread):
    """
    A Thread subclass that can properly handle exceptions.
    Taken from Stack Overflow: https://stackoverflow.com/questions/2829329/catch-a-threads-exception-in-the-caller-thread

    Please make sure that the target function of this thread
    has a `stop_event` attribute that is a boolean
    and that the function checks this attribute periodically and exits if it's set,
    so that we can signal to the thread to stop if we need to.
    """
    def run(self):
        self.exc = None
        self.ret = None

        if self._target and not hasattr(self._target, 'stop_event'):
            raise ValueError("The target function of a PropagatingThread must have a 'stop_event' attribute that is a boolean, so that we can signal to the thread to stop if needed.")

        try:
            self.ret = self._target(*self._args, **self._kwargs)
        except BaseException as e:
            self.exc = e

    def kill(self, timeout_s=10):
        """
        Kill this thread. Note that this is not a graceful shutdown, so use with caution.
        """
        if self.is_alive():
            # The target function should be checking for a boolean stop_event.
            # We set that event here to signal to the thread that it should stop what it's doing and exit.
            if hasattr(self._target, 'stop_event'):
                self._target.stop_event = True

        self.join(timeout=timeout_s)

    def join(self, timeout=None):
        super().join(timeout)
        if self.exc:
            raise self.exc

        if hasattr(self, 'ret'):
            return self.ret
        else:
            return None


############### Logging Wrapper ####################
def critical(msg: str):
    logging.getLogger(LOGGER_NAME).critical(msg)

def debug(msg: str):
    logging.getLogger(LOGGER_NAME).debug(msg)

def error(msg: str):
    logging.getLogger(LOGGER_NAME).error(msg)

def info(msg: str):
    logging.getLogger(LOGGER_NAME).info(msg)

def warning(msg: str):
    logging.getLogger(LOGGER_NAME).warning(msg)

def shutdown_logging():
    logging.shutdown()

###################################################

def argparse_file_path_type(arg: str) -> str:
    """
    Validates that the given file path exists on disk. To be used as the type argument in argparse.
    """
    if not os.path.exists(arg):
        raise argparse.ArgumentError()
    else:
        return arg

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

def default_build_location():
    """
    Get the default build (artifacts) location.
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

def git_tag(repo: str = None) -> str:
    """
    Return the short git hash of an Artie component's checkout.

    `repo`, if given, names a component - see workspace.known_repo_names(). Once the
    components live in separate repositories they each have their own hash, so whatever
    tags an artifact needs to say which component the artifact was built from. Passing
    nothing keeps the historical behaviour of reading the current directory's repository,
    which is what a single checkout of everything means.
    """
    cwd = workspace.repo_path(repo) if repo else None
    p = subprocess.run("git log --format='%h' -n 1".split(' '), capture_output=True, cwd=cwd)
    p.check_returncode()
    return p.stdout.decode('utf-8').strip().strip("'")

def host_platform() -> str:
    """
    Return the platform we are on. Should be of the form 'amd64' or 'arm64'.
    """
    p = platform.machine().lower()
    lookup = {
        "x86_64": "amd64",
        "aarch64": "arm64",
        "amd64": "amd64",
    }

    # Return amd64 or arm64 if possible, otherwise just pass the raw.lower() value through
    return lookup.get(p, p)

def kill_managed_threads(timeout_s=10):
    """
    Kill any threads that we have spawned and added to the _MANAGED_THREADS list.
    """
    for t in _MANAGED_THREADS:
        if t.is_alive():
            warning(f"Killing thread {t.name} that is still alive...")
            t.kill(timeout_s=timeout_s)

def manage_timeout(func, timeout_s: int, *args, **kwargs):
    """
    Runs `func` with `args` and `kwargs` to completion, or until `timeout_s` seconds
    has elapsed, at which point it raises a TimeoutError.

    Note that `func` should be designed to be run in a thread and must have a `stop_event` attribute that is a boolean,
    and should check this attribute periodically and exit if it's set, so that we can signal to the thread to stop if needed.
    """
    class TimeoutWrapper:
        def __init__(self, func, timeout_s) -> None:
            self.func = func
            self.timeout_s = timeout_s
            self.ret = None
            self._stop_event = False

        @property
        def stop_event(self):
            return self._stop_event

        @stop_event.setter
        def stop_event(self, value):
            self._stop_event = value
            self.func.stop_event = value

        def __call__(self, *args, **kwargs):
            try:
                self.ret = self.func(*args, **kwargs)
            except docker_errors.ContainerError as e:
                # Docker exceptions are not pickleable and so can't be propagated across the
                # test task boundary into the infrastructure module. It just hangs if you try.
                raise Exception(f"Container failed to start: {e}")

    if not hasattr(func, 'stop_event'):
        raise ValueError("The function passed to manage_timeout must have a 'stop_event' attribute that is a boolean, so that we can signal to it to stop if needed.")

    wrapper = TimeoutWrapper(func, timeout_s)
    t = PropagatingThread(target=wrapper, args=args, kwargs=kwargs, daemon=True)
    _MANAGED_THREADS.append(t)
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
        # Timeout. But let's wait a little longer to hopefully allow the thread to complete so the resources
        # such as Docker containers get cleaned up.
        warning(f"Function {name} timed out after {timeout_s} seconds. Waiting a little longer for it to hopefully finish cleaning up resources...")
        t.join(timeout=10)
        raise TimeoutError(f"Trying to run function {name} failed with a timeout.")
    return wrapper.ret

def replace_vars_in_string(s: str, vars_dict: dict[str, str]|argparse.Namespace|None=None, incomplete_ok=False) -> str:
    """
    Replace variables in the given string using the provided dictionary
    or argparse namespace.

    Variables are denoted by ${VAR_NAME}.

    Special variables ${REPO_ROOT} and ${GIT_TAG} are always replaced.

    :param s: The input string with variables.
    :param vars_dict: A dictionary mapping variable names to their values or an argparse.Namespace. Capitalization is ignored.
    :param incomplete_ok: If True, do not raise an error if a variable is not found.
    :return: The string with variables replaced.
    """
    s = str(s)

    if '${REPO_ROOT}' in s:
        s = s.replace("${REPO_ROOT}", repo_root())

    # ${REPO:<name>} resolves to the checkout directory of another Artie component, so a
    # task can reach across a repository boundary explicitly instead of assuming that
    # everything sits under one root. A function replacement is used rather than a plain
    # string so that Windows backslashes are not treated as regex escapes.
    if '${REPO:' in s:
        s = _REPO_REF_PATTERN.sub(lambda m: workspace.repo_path(m.group("repo_name")), s)

    if '${GIT_TAG}' in s:
        s = s.replace("${GIT_TAG}", git_tag())

    if vars_dict is None:
        vars_dict = {}
    elif isinstance(vars_dict, argparse.Namespace):
        vars_dict = vars(vars_dict)

    pattern = re.compile(r"\$\{(?P<var_name>\w+)\}")
    for match in pattern.finditer(s):
        var_name = match.group("var_name")
        if var_name in vars_dict or var_name.lower() in vars_dict:
            key = var_name if var_name in vars_dict else var_name.lower()
            s = s.replace(match.group(0), str(vars_dict[key]))
        elif not incomplete_ok:
            raise KeyError(f"Variable '{var_name}' not found in the provided dictionary or namespace.")

    return s

def repo_root() -> str:
    """
    Return the absolute path of the root of the Artie repository.

    Deprecated in favour of `workspace.repo_path(<component>)`. This only remains
    meaningful while Artie's components all live in one repository; anything that refers
    to a specific component should name it rather than assume a shared root.
    """
    return workspace.monorepo_root()

def set_up_logging(args):
    """
    Set up the logging for this process.
    """
    format = "[<%(asctime)s> %(processName)s (%(levelname)s)]: %(message)s"
    if not hasattr(args, "loglevel"):
        setattr(args, "loglevel", "info")
    level = getattr(logging, args.loglevel.upper())

    stream_handler= logging.StreamHandler(sys.stdout)
    handlers = [stream_handler]
    if hasattr(args, 'output') and args.output:
        file_handler = logging.FileHandler(args.output, mode='w')
        handlers += [file_handler]

    # Set up root logger to log only at WARNING or above
    rootlevel = level if level > logging.WARNING else logging.WARNING
    logging.basicConfig(format=format, level=rootlevel, force=True, handlers=handlers)

    # Set up our logger to be whatever user has requested or else the default
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)

def scp_from(ip: str, uname: str, password: str, target: str, dest: str|None) -> None|str:
    """
    Copy the file from `target` on the remote machine to the `dest` on the local machine.
    If `dest` is `None`, we return the file's contents (as bytes).
    """
    c = fabric.Connection(ip, uname, forward_agent=True, connect_timeout=30, connect_kwargs={'password': password})
    if dest is None:
        return c.run(f"cat {target}", hide=True).stdout
    else:
        c.get(target, local=dest)

def scp_to(ip: str, uname: str, password: str, target: str, dest: str):
    """
    Copy the file from `target` on the local machine to the `dest` on the remote machine.
    """
    c = fabric.Connection(ip, uname, forward_agent=True, connect_timeout=30, connect_kwargs={'password': password})
    c.put(target, remote=dest)

def ssh(cmd: str, ip: str, uname: str, password: str, timeout_s=30, fail_okay=False, additional_responders=None):
    """
    Execute the given command at the given remote host. Will handle 'sudo' password use
    if the command invokes sudo.

    If `fail_okay` is given, we ignore any errors on the server that result from running
    the given command.

    If `additional_responders` is given, it should be a list of tuples of the form (pattern: str, response: str)
    that will be used to respond to prompts from the remote host.
    """
    c = fabric.Connection(ip, uname, forward_agent=True, connect_timeout=30, connect_kwargs={'password': password})

    sudopass = invoke.watchers.Responder(pattern=r'\[sudo\] password:', response=password)
    watchers = [sudopass]
    if additional_responders:
        for pattern, response in additional_responders:
            watchers.append(invoke.watchers.Responder(pattern=pattern, response=response))

    c.run(cmd, pty=True, watchers=watchers, timeout=timeout_s, hide=True, warn=fail_okay)

def _resolve_hostname(user_input: str) -> str:
    """
    Resolve the given raw user input (which may be an IP address or a hostname) to an IP address.
    Attempt to resolve to IPv4, fallback to IPv6 if not available.
    """
    try:
        addrinfo = socket.getaddrinfo(user_input, 6443)
    except socket.gaierror as e:
        raise ValueError(f"Could not resolve the given IP address or hostname: {user_input}: {e}")

    for info in addrinfo:
        family, t, proto, canonname, sockaddr = info
        if family == socket.AddressFamily.AF_INET:
            # As soon as we find an IPv4, break (otherwise we'll use whatever IPv6 we find last)
            ip, port = sockaddr
            break
        elif family == socket.AddressFamily.AF_INET6:
            ip, port, _, _ = sockaddr

    return ip

def validate_input_ip(user_input: str) -> str:
    """
    Validates that the input is an IP address and returns it if so. Otherwise throws an exception.
    If the IP address is a hostname, tries to resolve it to an IP address.
    """
    try:
        ip = _resolve_hostname(user_input)
    except ValueError as e:
        print(e)
        raise argparse.ArgumentError()

    try:
        _ = ipaddress.ip_address(ip)
    except ValueError:
        raise argparse.ArgumentError()
    return ip

def verify_ssh_connection(ip: str, uname: str, password: str) -> Tuple[bool, Exception|None]:
    """
    Return whether we can access the given IP address with the given credentials or not.
    If we can't, we return the exception we got while trying (if any).
    """
    c = fabric.Connection(ip, uname, forward_agent=True, connect_timeout=30, connect_kwargs={'password': password})
    try:
        c.run("echo 'testing connection to Artie from Artie Tool'", timeout=30, hide=True)
        return True, None
    except Exception as e:
        return False, e
