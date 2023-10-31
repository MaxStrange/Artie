"""
Machinery for handling Docker containers.
"""
from . import common
from typing import Any, Dict
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

API_CALL_TIMEOUT_S = 30

class DockerImageName:
    def __init__(self, repo: str, name: str, tag: str) -> None:
        self.repo = repo
        self.name = name
        self.tag = tag

    def __str__(self) -> str:
        return f"{self.repo}{self.name}:{self.tag}"

    def __repr__(self) -> str:
        return str(self)

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

def build_docker_image(args, builddpath: str, docker_image_name: DockerImageName, buildx=True, fpaths=None, context='.', extra_build_args="", dockerfile_name="Dockerfile", platform=None):
    """
    Common stuff that a whole bunch of BuildTasks do when building a Docker image.

    Args
    ----
    - builddpath: The directory in which to find the Dockerfile
    - docker_image_name: The repo, name, and tag of the Docker image to build and potentially push.
    - buildx: If given, we use buildx to build for ARM64. Otherwise, we build using standard Docker build.
    - fpaths: If given, should be a list of file paths to items that we will copy into a builddpath/tmp folder for copying into the img.
    - context: The build context. Defaults to the path where the Dockerfile is found, but it is also
               common to use one folder up from that, in which case, use '..'
    - extra_build_args: If given, we insert into the docker build string.
    - dockerfile_name: The name of the Dockerfile, typically it is just 'Dockerfile', but could be something else.
    - platform: Must be a supported Docker build platform. If using buildx, this defaults to linux/arm64 and if not, linux/amd64.
    """
    tmpdpath = os.path.join(builddpath, "tmp")
    os.makedirs(tmpdpath, exist_ok=True)
    common.info(f"Building Docker image and tagging it as {str(docker_image_name)}")

    # Determine platform
    if buildx and not platform:
        platform = "linux/arm64"
    elif not buildx and not platform:
        platform = "linux/amd64"

    # Retrieve dependencies
    if fpaths:
        for fpath in fpaths:
            tmp_fpath = os.path.join(tmpdpath, os.path.basename(fpath))
            common.info(f"Copying {fpath} to {tmp_fpath}")
            if os.path.exists(tmp_fpath):
                # Already present from a previous job. Overwrite.
                shutil.rmtree(tmp_fpath)

            if os.path.isfile(fpath):
                shutil.copyfile(fpath, tmp_fpath)
            else:
                shutil.copytree(fpath, tmp_fpath)

    # Build the Docker image
    extraargs = get_extra_docker_build_args(args)
    dockerargs = f"{extraargs} {extra_build_args}"
    if buildx:
        dockercmd = f"docker buildx build --load --platform {platform} -f {dockerfile_name} {dockerargs} -t {str(docker_image_name)} {context}"
    else:
        dockercmd = f"docker build -f {dockerfile_name} {dockerargs} -t {str(docker_image_name)} {context}"
    common.info(f"Running: {dockercmd}")
    subprocess.run(dockercmd.split(), cwd=builddpath).check_returncode()

    # Push the Docker image to the chosen repo (if given)
    if args.docker_repo is not None:
        push_docker_image(args, docker_image_name)

    return docker_image_name

def check_and_pull_if_docker_image_exists(args, imgname: DockerImageName) -> bool:
    """
    Returns whether the given Docker image exists and pulls it if it exists remotely and can be pulled.
    """
    common.info(f"Checking if {imgname} exists locally...")
    docker_image_ids = subprocess.run(f"docker images {imgname} --quiet".split(), capture_output=True).stdout.decode('utf-8').split()
    for img_id in docker_image_ids:
        if img_id != '':
            common.info(f"Found {imgname} locally")
            return True

    # Can't find it locally. Check if we can pull it.
    common.info(f"Can't find {imgname} locally. Trying to pull it.")
    try:
        pull_docker_image(args, imgname)
        common.info(f"Pulled {imgname}")
        return True
    except Exception as e:
        common.info(f"Cannot find {imgname} locally or remotely, or was unable to pull it from remote: {e}")
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
        common.info(f"Sending stop signal to container {short_id}...")
        stop_docker_container(docker_id)

def construct_docker_image_name(args, name, platform=None, repo_prefix=None, tag=None) -> DockerImageName:
    """
    Returns a DockerImageName object.

    `repo_prefix` defaults to "".
    `tag` defaults to git tag.
    """
    if tag is None:
        tag = common.git_tag() if not hasattr(args, 'docker_tag') or args.docker_tag is None else args.docker_tag

    if repo_prefix is None:
        repo_prefix = "" if not hasattr(args, 'docker_repo') or args.docker_repo is None else args.docker_repo
        repo_prefix = repo_prefix + "/" if repo_prefix and not repo_prefix.endswith('/') else repo_prefix

    if platform and "/" in platform:
        platform = platform.split('/')[1]

    if platform is not None and platform not in ("amd64", "arm64"):
        raise ValueError(f"Platform should be one of 'amd64', 'arm64', or of the form '*/amd64' or '*/arm64', but is {platform}")

    tag_and_platform = f"{tag}-{platform}" if platform else f"{tag}"
    return DockerImageName(repo_prefix, name, tag_and_platform)

def get_tag_from_name(docker_image_name: str|DockerImageName) -> str:
    """
    Returns the tag name of the docker image.
    """
    if issubclass(type(docker_image_name), DockerImageName):
        return docker_image_name.tag
    else:
        # Thank you, Stack Overflow: https://stackoverflow.com/questions/74990220/how-to-use-docker-image-tag-parsing-regex-in-javascript
        # With a minor modification
        r = re.compile("^(?P<repository>[\w.\-_]+(?::\d+|)|)(?:/|)(?P<image>[a-z0-9.\-_]+(?:/[a-z0-9.\-_]+|))(:(?P<tag>[\w.\-_]{1,127})|)$")
        o = r.match(docker_image_name)
        if not o:
            errmsg = f"Could not understand the given string as a Docker image ID: {docker_image_name}"
            common.error(errmsg)
            raise ValueError(errmsg)
        # for the future, in case you are wondering, groupdict will also get: 'repository' and 'image'
        return o.groupdict().get('tag', "")

def get_extra_docker_build_args(args):
    """
    Returns a commandline string to add to a Docker build (or buildx) invocation, based on
    common args.
    """
    ret = ""
    if args.docker_no_cache:
        ret += " --no-cache"
    return ret

def _parse_json_for_names_manually(json_output: str) -> Dict[str, str]:
    # Example: "Name":"eyebrows-itest-api-server"
    pattern_name = re.compile("\"Name\":\"(?P<name>)\"")
    # Example: "ID":"791e54dd426b"
    pattern_id = re.compile("\"ID\":\"(?P<id>)\"")
    ids = {}
    for line in json_output.splitlines():
        if 'Name' and 'ID' in line:
            match_name = pattern_name.match(line)
            match_id = pattern_id.match(line)
            if match_name and match_id:
                name = match_name.groupdict().get('name', '')
                idval = match_id.groupdict().get('id', '')
                if name and idval:
                    ids[name] = idval
    if not ids:
        errmsg = f"Cannot decode JSON output. Raw output: {json_output}"
        raise OSError(errmsg)
    return ids

def _parse_json_workaround(json_output: str):
    # On some platforms, we have to do the JSON decoding via this workaround
    ids = {}
    for line in json_output.splitlines():
        try:
            decoded_output = json.loads(line)
            ids[decoded_output['Name']] = decoded_output['ID']
        except json.JSONDecodeError as e1:
            common.error(f"Cannot understand JSON output. Got an exception while trying to decode the raw output and an exception when trying a workaround: {e1}. Raw output looks like this: {json_output}")
            raise e1
    if not ids:
        # Aaaand another work around
        ids = _parse_json_for_names_manually(json_output)

    return ids

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
    common.info(f"Running {cmd} with environment variables: {envs}")
    envs = envs | os.environ  # Merge our dict with the current shell's environment (this is a dict-merge syntax introduced in 3.9)
    p = subprocess.run(cmd.split(), cwd=cwd, capture_output=True, env=envs)
    if p.returncode != 0:
        common.error(f"Failed to run cmd: {cmd}")
        common.error(f"Subprocess's stderr: {p.stderr.decode('utf-8')}")
        common.error(f"Subprocess's stdout: {p.stdout.decode('utf-8')}")
        p.check_returncode()

    # Now return all the Docker pids we launched
    cmd = f"docker compose -p {project_name} -f {fname} ps --format json"
    p = subprocess.run(cmd.split(), cwd=cwd, capture_output=True, env=envs, timeout=startup_timeout_s)
    if p.returncode != 0:
        common.error(f"Failed to run cmd: {cmd}")
        common.error(f"Subprocess's stderr: {p.stderr.decode('utf-8')}")
        common.error(f"Subprocess's stdout: {p.stdout.decode('utf-8')}")
        p.check_returncode()
    json_output = p.stdout.decode('utf-8')
    try:
        decoded_output = json.loads(json_output)
        ids = {jsonobject['Name']: jsonobject['ID'] for jsonobject in decoded_output}
    except json.JSONDecodeError:
        ids = _parse_json_workaround(json_output)
    return ids

def compose_down(project_name: str, cwd: str, fname: str, envs=None):
    """
    Brings down a docker compose and cleans up all the containers.
    """
    cmd = f"docker compose -p {project_name} -f {fname} down --remove-orphans --volumes"
    common.info(f"Running {cmd} with environment variables: {envs}")
    envs = envs | os.environ  # Merge our dict with the current shell's environment (this is a dict-merge syntax introduced in 3.9)
    p = subprocess.run(cmd.split(), cwd=cwd, capture_output=True, env=envs)
    if p.returncode != 0:
        common.error(f"Failed to run cmd: {cmd}")
        common.error(f"Subprocess's stderr: {p.stderr.decode('utf-8')}")
        common.error(f"Subprocess's stdout: {p.stdout.decode('utf-8')}")
        p.check_returncode()

    # Now remove all the containers we just stopped
    cmd = f"docker compose -p {project_name} -f {fname} rm --force --stop --volumes"
    p = subprocess.run(cmd.split(), cwd=cwd, capture_output=True, env=envs)
    if p.returncode != 0:
        common.error(f"Failed to run cmd: {cmd}")
        common.error(f"Subprocess's stderr: {p.stderr.decode('utf-8')}")
        common.error(f"Subprocess's stdout: {p.stdout.decode('utf-8')}")
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
        common.info(f"Copying {short_id}:{path} to {path_on_host}...")
        targetpath = os.path.join(path_on_host, path)
        if os.path.isfile(targetpath):
            os.remove(targetpath)
        elif os.path.isdir(targetpath):
            shutil.rmtree(targetpath)
        try:
            subprocess.run(f"docker cp {docker_id}:{path} {path_on_host}".split(), stdout=subprocess.DEVNULL).check_returncode()
        except subprocess.CalledProcessError as e:
            try:
                items = subprocess.run(f"docker exec {docker_id} ls {os.path.dirname(path)}".split(), capture_output=True, encoding='utf-8').stdout
            except Exception:
                items = "Could not run the debugging command to find any items in the container."
            common.error(f"Could not run the docker cp command. Items found in container: {items}; error: {e}")
            raise e

    # Stop the container
    common.info(f"Sending stop signal to container {short_id}...")
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
    client = docker.from_env(timeout=API_CALL_TIMEOUT_S)
    try:
        ret = client.containers.get(name_or_pid)
    except docker_errors.NotFound:
        ret = None
    return ret

def docker_login(args):
    """
    Log in to the Docker API.
    """
    common.info(f"Attempting to log into Docker registry: {args.docker_repo} with username {args.docker_username}")
    pswd = args.docker_password if args.docker_password is not None else os.environ.get("ARTIE_TOOL_DOCKER_PASSWORD", None)
    if pswd is None:
        raise ValueError(f"Given a docker username ({args.docker_username}) for registry {args.docker_repo}, but no password was found in --docker-password or ARTIE_TOOL_DOCKER_PASSWORD")

    # If this is for Dockerhub, don't use the registry
    client = docker.from_env(timeout=API_CALL_TIMEOUT_S)
    if re.compile(".+://.+").match(args.docker_repo):
        client.login(username=args.docker_username, password=pswd, registry=args.docker_repo)
    else:
        client.login(username=args.docker_username, password=pswd)

def check_for_network(network_name: str) -> bool:
    """
    Returns `True` if we can find a Docker network with the given name. `False` otherwise.
    """
    client = docker.from_env(timeout=API_CALL_TIMEOUT_S)
    networks = client.networks.list(network_name)
    return len(networks) > 0

def remove_network(network_name: str):
    """
    Removes the Docker network with the given name from the system. If the network cannot be
    found, we do nothing.
    """
    if not check_for_network(network_name):
        return

    client = docker.from_env(timeout=API_CALL_TIMEOUT_S)
    networks = client.networks.list(network_name)
    if len(networks) > 1:
        raise ValueError(f"Cannot delete network with name {network_name}. Found multiple matching networks somehow: {[n.name for n in networks]}")
    network = networks[0]

    # Ensure there are no containers using this network. If there are any, remove them - they shouldn't still be using this network.
    # Sometimes this can happen if a test times out waiting for a container to exit. We do our best to clean up, but sometimes we can't
    # guarantee it.
    network.reload()
    for container in network.containers:
        common.warning(f"A container ({container.name}) is still using network {network_name}. Attempting to stop the container.")
        container.stop()
        if container.status == "running":
            common.warning(f"Container {container.name} did not stop. Attempting to kill.")
            container.kill()
            if container.status == "running":
                container.wait(timeout=10)
                if container.status == "running":
                    common.error(f"Container {container.name} cannot be stopped or killed. Attempting to remove network, but will likely fail.")

    network.remove()

def add_network(network_name: str, exists_okay=False):
    """
    Adds a Docker network with the given name to this system. If the network already exists, we
    raise an ValueError exception, unless exists_okay=True.
    """
    if not exists_okay and check_for_network(network_name):
        raise ValueError(f"Cannot create Docker network {network_name} as it already exists.")

    client = docker.from_env(timeout=API_CALL_TIMEOUT_S)
    client.networks.create(network_name)

def _try_pull_once(docker_image_name: DockerImageName, client):
    try:
        ret = client.api.pull(f"{docker_image_name.repo}{docker_image_name.name}", docker_image_name.tag, stream=True, decode=True)
        for line in ret:
            if 'error' in line:
                common.warning(line)
                return Exception(f"{line['error']}")
            else:
                common.info(line['status'] if 'status' in line else line)
    except docker_errors.APIError as e:
        return e

def pull_docker_image(args, imgname: DockerImageName, nretries=3):
    """
    Tries to pull the given image, raising an exception if it can't.
    """
    if args.docker_username is not None:
        docker_login(args)

    # Check if the docker image exists remotely before attempting to pull it a bunch
    p = subprocess.run(f"docker manifest inspect {imgname}".split(), capture_output=True, encoding='utf-8')
    if p.returncode != 0:
        raise Exception(f"Cannot find {imgname} remotely, so cannot pull it: {p.stderr}\n{p.stdout}".strip())

    client = docker.from_env(timeout=API_CALL_TIMEOUT_S)
    err = None
    for i in range(nretries):
        if i == 0:
            common.info(f"Pulling Docker image {imgname}...")
        else:
            common.warning(f"Pulling failed. Retrying {imgname}...")
            time.sleep(1)

        err = _try_pull_once(imgname, client)
        if err:
            continue

    if err:
        raise Exception(f"Could not pull {imgname}: {err}")

def _try_push_once(docker_image_name: DockerImageName, client):
    try:
        ret = client.api.push(f"{docker_image_name.repo}{docker_image_name.name}", docker_image_name.tag, stream=True, decode=True)
        for line in ret:
            if 'error' in line:
                common.warning(line)
                return Exception(f"{line['error']}")
            else:
                common.info(line['status'] if 'status' in line else line)
    except docker_errors.APIError as e:
        return e

def push_docker_image(args, docker_image_name: DockerImageName, nretries=3):
    """
    Attempts to push the given docker image up to n times.

    If args contains a username, we also login first.
    """
    if args.docker_username is not None:
        docker_login(args)

    client = docker.from_env(timeout=API_CALL_TIMEOUT_S)
    err = None
    for i in range(nretries):
        if i == 0:
            common.info(f"Pushing Docker image {docker_image_name}...")
        else:
            common.warning(f"Pushing failed: {err}: Retrying {docker_image_name}...")
            time.sleep(1)

        err = _try_push_once(docker_image_name, client)
        if err is None:
            break

    if err is not None:
        raise Exception(f"Could not push {docker_image_name}: {err}")

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
    client = docker.from_env(timeout=API_CALL_TIMEOUT_S)
    common.info(f"Running command: {cmd} ; using kwargs: {kwargs}")
    stdout = common.manage_timeout(client.containers.run, timeout_s, image_name, cmd, remove=True, stdout=True, stderr=True, **kwargs)

    if log_to_stdout and stdout is not None:
        common.info(f"Docker output: {stdout.decode()}")

    if stdout is not None:
        stdout = stdout.decode()

    return stdout

def stop_docker_container(image_id):
    """
    Stops the given Docker container if it is running. Does nothing if it isn't.
    """
    subprocess.run(f"docker stop {image_id}".split(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def start_docker_container(image_name: str|DockerImageName, cmd, **kwargs):
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
    client = docker.from_env(timeout=API_CALL_TIMEOUT_S)
    common.info(f"Running command: {cmd}")
    container = client.containers.run(str(image_name), cmd, remove=True, detach=True, **kwargs)
    return container
