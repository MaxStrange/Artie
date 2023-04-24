"""
Machinery for handling Docker containers.
"""
from . import common
from typing import Dict
import json
import logging
import os
import random
import re
import shutil
import string
import subprocess
import time

try:
    import docker
    from docker import errors as docker_errors
    from docker.models.containers import Container
except ModuleNotFoundError:
    logging.error("'docker' not installed. Make sure to install dependencies with 'pip install -r requirements.txt'")
    exit(1)

def _get_cidfile_path():
    """
    Return a location to put a Docker invocation's cidfile.
    """
    scratch_location = common.get_scratch_location()
    cidfile_fpath = os.path.join(scratch_location, f"_docker_id_{''.join(random.choices(string.ascii_letters, k=12))}.txt")
    return cidfile_fpath

def _get_docker_id_from_cidfile(fpath):
    """
    Return the Docker ID from the given CIDfile.
    """
    docker_id = open(fpath).read().strip()
    return docker_id

def clean_build_location(args, builddpath: str):
    """
    Clean up after a build_docker_image() call.
    """
    tmpdpath = os.path.join(builddpath, "tmp")
    if os.path.exists(tmpdpath):
        shutil.rmtree(tmpdpath, ignore_errors=True)

def build_docker_image(args, builddpath: str, simplified_img_name: str, buildx=True, fpaths=None, context='.', extra_build_args="", dockerfile_name="Dockerfile"):
    """
    Common stuff that a whole bunch of BuildTasks do when building a Docker image.

    Args
    ----
    - builddpath: The directory in which to find the Dockerfile
    - simplified_img_name: The simplified image name of the Docker image to produce
    - buildx: If given, we use buildx to build for ARM64. Otherwise, we build using standard Docker build.
    - fpaths: If given, should be a list of file paths to items that we will copy into a builddpath/tmp folder for copying into the img.
    - context: The build context. Defaults to the path where the Dockerfile is found, but it is also
               common to use one folder up from that, in which case, use '..'
    - extra_build_args: If given, we insert into the docker build string.
    - dockerfile_name: The name of the Dockerfile, typically it is just 'Dockerfile', but could be something else.
    """
    tmpdpath = os.path.join(builddpath, "tmp")
    os.makedirs(tmpdpath, exist_ok=True)

    # Docker image name
    if is_simplified_name(simplified_img_name):
        docker_image_name = construct_docker_image_name(args, simplified_img_name)
    else:
        docker_image_name = simplified_img_name
    logging.info(f"Building Docker image and tagging it as {docker_image_name}")

    # Retrieve dependencies
    if fpaths:
        for fpath in fpaths:
            tmp_fpath = os.path.join(tmpdpath, os.path.basename(fpath))
            logging.info(f"Copying {fpath} to {tmp_fpath}")
            if os.path.isfile(fpath):
                shutil.copyfile(fpath, tmp_fpath)
            else:
                shutil.copytree(fpath, tmp_fpath)

    # Build the Docker image
    extraargs = get_extra_docker_build_args(args)
    dockerargs = f"{extraargs} {extra_build_args}"
    if buildx:
        dockercmd = f"docker buildx build --load --platform linux/arm64 -f {dockerfile_name} {dockerargs} -t {docker_image_name} {context}"
    else:
        dockercmd = f"docker build -f {dockerfile_name} {dockerargs} -t {docker_image_name} {context}"
    logging.info(f"Running: {dockercmd}")
    subprocess.run(dockercmd, cwd=builddpath).check_returncode()

    # Push the Docker image to the chosen repo (if given)
    if args.docker_repo is not None:
        push_docker_image(docker_image_name)

    return docker_image_name

def check_if_docker_image_exists(imgname: str) -> bool:
    """
    Returns whether the given Docker image (full name) exists in this system.
    """
    docker_image_ids = subprocess.run(f"docker images {imgname} --quiet", capture_output=True).stdout.decode('utf-8').split()
    for img_id in docker_image_ids:
        if img_id != '':
            return True
    return False

def clean_docker_containers():
    """
    Attempts to detect if any build process Docker containers are still around
    and then tries to stop them if so.
    """
    scratch_location = common.get_scratch_location()
    if not os.path.isdir(scratch_location):
        return

    docker_id_fpaths = []
    fnames = os.listdir(scratch_location)
    for fname in fnames:
        fpath = os.path.join(scratch_location, fname)
        if fname.startswith("_docker_id_"):
            docker_id_fpaths.append(fpath)

    for cidfile_fpath in docker_id_fpaths:
        # Get the docker ID
        docker_id = open(cidfile_fpath).read().strip()
        short_id = docker_id[:8]

        # Stop the container
        logging.info(f"Sending stop signal to container {short_id}...")
        stop_docker_container(docker_id)

def construct_docker_image_name(args, name, repo_prefix=None, tag=None) -> str:
    """
    Returns a string of the form "{repo_prefix}{name}:{tag}".

    `repo_prefix` defaults to "".
    `tag` defaults to git tag.
    """
    if tag is None:
        tag = common.git_tag() if not hasattr(args, 'docker_tag') or args.docker_tag is None else args.docker_tag

    if repo_prefix is None:
        repo_prefix = "" if not hasattr(args, 'docker_repo') or args.docker_repo is None else args.docker_repo + "/"

    return f"{repo_prefix}{name}:{tag}"

def get_extra_docker_build_args(args):
    """
    Returns a commandline string to add to a Docker build (or buildx) invocation, based on
    common args.
    """
    ret = ""
    if args.docker_no_cache:
        ret += " --no-cache"
    return ret

def compose(project_name: str, cwd: str, fname: str, startup_timeout_s: int, envs=None) -> Dict[str, str]:
    """
    Runs Docker compose on the given compose file from cwd.

    If `envs` is given, it should be a dict of names : values to export into the shell
    environment when running docker compose.

    `project_name` is the name of the Docker compose project, which allows the docker compose command
    to partition multiple runs of docker compose into separate namespaces it can interact with.

    Returns a dict of Docker container names to container pids (which are strings).
    """
    cmd = f"docker compose -p {project_name} -f {fname} up --detach --no-build --no-color --quiet-pull --wait-timeout {startup_timeout_s} --force-recreate --always-recreate-deps --renew-anon-volumes"
    logging.info(f"Running {cmd} with environment variables: {envs}")
    envs = envs | os.environ  # Merge our dict with the current shell's environment (this is a dict-merge syntax introduced in 3.9)
    p = subprocess.run(cmd.split(), cwd=cwd, capture_output=True, env=envs)
    if p.returncode != 0:
        logging.error(f"Failed to run cmd: {cmd}")
        logging.error(f"Subprocess's stderr: {p.stderr.decode('utf-8')}")
        logging.error(f"Subprocess's stdout: {p.stdout.decode('utf-8')}")
        p.check_returncode()

    # Now return all the Docker pids we launched
    cmd = f"docker compose -p {project_name} -f {fname} ps --format json"
    p = subprocess.run(cmd.split(), cwd=cwd, capture_output=True, env=envs, timeout=startup_timeout_s)
    if p.returncode != 0:
        logging.error(f"Failed to run cmd: {cmd}")
        logging.error(f"Subprocess's stderr: {p.stderr.decode('utf-8')}")
        logging.error(f"Subprocess's stdout: {p.stdout.decode('utf-8')}")
        p.check_returncode()
    json_output = p.stdout.decode('utf-8')
    decoded_output = json.loads(json_output)
    ids = {jsonobject['Name']: jsonobject['ID'] for jsonobject in decoded_output}
    return ids

def compose_down(project_name: str, cwd: str, fname: str, envs=None):
    """
    Brings down a docker compose and cleans up all the containers.
    """
    cmd = f"docker compose -p {project_name} -f {fname} down --remove-orphans --volumes"
    logging.info(f"Running {cmd} with environment variables: {envs}")
    envs = envs | os.environ  # Merge our dict with the current shell's environment (this is a dict-merge syntax introduced in 3.9)
    p = subprocess.run(cmd.split(), cwd=cwd, capture_output=True, env=envs)
    if p.returncode != 0:
        logging.error(f"Failed to run cmd: {cmd}")
        logging.error(f"Subprocess's stderr: {p.stderr.decode('utf-8')}")
        logging.error(f"Subprocess's stdout: {p.stdout.decode('utf-8')}")
        p.check_returncode()

    # Now remove all the containers we just stopped
    cmd = f"docker compose -p {project_name} -f {fname} rm --force --stop --volumes"
    p = subprocess.run(cmd.split(), cwd=cwd, capture_output=True, env=envs)
    if p.returncode != 0:
        logging.error(f"Failed to run cmd: {cmd}")
        logging.error(f"Subprocess's stderr: {p.stderr.decode('utf-8')}")
        logging.error(f"Subprocess's stdout: {p.stdout.decode('utf-8')}")
        p.check_returncode()

def docker_copy(image: str, paths_in_container: list, path_on_host: str):
    """
    Copy a given item or list of items from a Docker image onto the host.
    """
    cidfile_fpath = _get_cidfile_path()
    p = subprocess.Popen(["docker", "run", "--rm", "--cidfile", cidfile_fpath, image], stdout=subprocess.DEVNULL)

    # Give it a moment to let the container start up
    time.sleep(1)

    # Get the docker ID
    docker_id = _get_docker_id_from_cidfile(cidfile_fpath)
    short_id = docker_id[:8]

    if not isinstance(paths_in_container, list):
        paths_in_container = [paths_in_container]

    # Do the actual copy
    for path in paths_in_container:
        logging.info(f"Copying {short_id}:{path} to {path_on_host}...")
        targetpath = os.path.join(path_on_host, path)
        if os.path.isfile(targetpath):
            os.remove(targetpath)
        elif os.path.isdir(targetpath):
            shutil.rmtree(targetpath)
        try:
            subprocess.run(f"docker cp {docker_id}:{path} {path_on_host}", stdout=subprocess.DEVNULL).check_returncode()
        except subprocess.CalledProcessError as e:
            try:
                items = subprocess.run(f"docker exec {docker_id} ls {os.path.dirname(path)}", capture_output=True, encoding='utf-8').stdout
            except Exception:
                items = "Could not run the debugging command to find any items in the container."
            logging.error(f"Could not run the docker cp command. Items found in container: {items}; error: {e}")
            raise e

    # Stop the container
    logging.info(f"Sending stop signal to container {short_id}...")
    stop_docker_container(docker_id)
    p.wait()

def get_container_name_from_pid(pid: str, strip=False) -> str:
    """
    Returns the container name from the given container PID. Raises a KeyError
    if we can't find the name attribute on the container, and a docker_errors.NotFound
    error if can't find the container at all.

    By default, compose container name's come with a leading '/'. Use `strip`
    if you want this removed.
    """
    container = get_container(pid)
    name = container.attrs.get('Name')
    if name is None:
        raise KeyError(f"Cannot find 'Name' attribute on container {pid}")

    if strip:
        name = name.lstrip('/')

    return name

def get_container(name_or_pid: str) -> Container:
    """
    Returns a Container object from the given `name_or_pid` string.
    Returns None if we can't find the container.
    """
    client = docker.from_env()
    try:
        ret = client.containers.get(name_or_pid)
    except docker_errors.NotFound:
        ret = None
    return ret

def is_simplified_name(name: str) -> bool:
    pattern = re.compile(".+/.+:.+")
    return not pattern.match(name)

def push_docker_image(docker_image_name, nretries=2):
    """
    Attempts to push the given docker image up to n times.
    """
    for i in range(nretries):
        if i == 0:
            logging.info(f"Pushing Docker image {docker_image_name}...")
        else:
            logging.warning(f"Pushing failed. Retrying {docker_image_name}...")
            time.sleep(1)

        p = subprocess.run(f"docker push {docker_image_name}")
        if p.returncode == 0:
            return

def run_docker_container(image_name, cmd, timeout_s=30, log_to_stdout=False, **kwargs):
    """
    Like `start_docker_container()`, but runs to completion before returning
    (or it times out).

    If `quiet` is False, we return None, otherwise we return the stdout of the run container.

    Args
    ----
    - image_name: The name of the Docker image to run as a container
    - cmd: The command to run inside the Docker container
    - timeout_s: Timeout in seconds.
    - log_to_stdout: If given, we log the Docker logs to the console.
    - kwargs: Additional kwargs to pass onto the Docker SDK.
    """
    client = docker.from_env()
    logging.info(f"Running command: {cmd}")
    stdout = common.manage_timeout(client.containers.run, timeout_s, image_name, cmd, remove=True, stdout=True, stderr=True, **kwargs)
    if log_to_stdout and stdout is not None:
        logging.info(f"Docker output: {stdout.decode()}")
    return stdout

def stop_docker_container(image_id):
    """
    Stops the given Docker container if it is running. Does nothing if it isn't.
    """
    subprocess.run(f"docker stop {image_id}", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def start_docker_container(image_name, cmd, **kwargs):
    """
    Starts a Docker container with the given command executed inside the container
    and returns a `Container` object from the `docker` package after detaching from it.

    Args
    ----
    - image_name: The name of the Docker image to run as a container
    - cmd: The command to run inside the Docker container
    - log_to_stdout: If given, we log the Docker logs to the console.
    - kwargs: Keyword arguments for docker.run() command. See https://docker-py.readthedocs.io/en/stable/containers.html#docker.models.containers.ContainerCollection.run
    """
    client = docker.from_env()
    logging.info(f"Running command: {cmd}")
    container = client.containers.run(image_name, cmd, remove=True, detach=True, **kwargs)
    return container
