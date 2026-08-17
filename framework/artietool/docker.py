"""
Machinery for handling Docker containers.
"""
from . import common
from typing import Any, Dict, List
import json
import logging
import os
import random
import re
import shutil
import string
import subprocess
import threading
import time

try:
    import docker
    from docker import errors as docker_errors
    from docker.models.containers import Container
except ModuleNotFoundError:
    logging.error("'docker' not installed. Make sure to install dependencies with 'pip install -r requirements.txt'")
    exit(1)

API_CALL_TIMEOUT_S = 600
BUILD_NRETRIES = 3
CONTAINER_START_TIMEOUT_S = 60

# Cached result of `docker buildx inspect` driver detection (per process)
_BUILDX_DRIVER = None

# Cached result of the Docker server's architecture (per process)
_HOST_ARCH = None

class DockerImageName:
    def __init__(self, repo: str, name: str, tag: str) -> None:
        self.repo = repo
        self.name = name
        self.tag = tag

    def __str__(self) -> str:
        return f"{self.repo}{self.name}:{self.tag}"

    def __repr__(self) -> str:
        return str(self)

class DockerManifest:
    def __init__(self, name: str, image_names: List[str], insecure: bool) -> None:
        self.name = name
        self.image_names = image_names
        self.insecure = insecure

    def __str__(self) -> str:
        return f"Docker Manifest List {self.name}"

    def __repr__(self) -> str:
        return str(self)

class DockerRunner:
    """
    A class for running Docker containers that periodically checks for
    a stop signal and stops the container if it receives one. This is useful for running Docker
    containers as part of a TestJob and ensuring that they are cleaned up properly even if the test fails or is interrupted.
    """
    def __init__(self, client: docker.DockerClient, image: str, cmd: str, **kwargs) -> None:
        self.client = client
        self.image = image
        self.cmd = cmd
        self.kwargs = kwargs
        self.container = None
        self.stop_event = False
        self.container_output = None

    def __call__(self):
        common.info(f"Starting Docker container with image {self.image} and command {self.cmd}...")
        self.container = self.client.containers.run(self.image, command=self.cmd, stdout=True, stderr=True, detach=True, **self.kwargs)
        common.info(f"Started Docker container with image {self.image} with ID {self.container.id}. Waiting for it to finish or for a stop signal...")

        while not self.stop_event:
            time.sleep(1)
            self.container.reload()  # Refresh the container's status
            if self.container.status.lower() in ("exited", "dead"):
                common.info(f"Docker container with image {self.image} and ID {self.container.id} has finished with status {self.container.status}.")
                break

        if self.container:
            try:
                common.info(f"Stop signal received or container finished. Stopping container {self.image} - {self.container.id}...")
                self.container.stop(timeout=10)
                self.container_output = self.container.logs(stdout=True, stderr=True)
                self.container.remove(force=True)
                common.info(f"Container {self.image} - {self.container.id} stopped.")
            except docker_errors.NotFound:
                common.debug(f"Container with ID {self.container.id} not found when trying to stop it. It may have already stopped on its own, which is fine.")
            except docker_errors.APIError as e:
                common.warning(f"Got an exception while trying to stop Docker container with ID {self.container.id}. Exception: {e}")

    def get_container_output(self):
        return self.container_output

def _get_cidfile_path():
    """
    Return a location to put a Docker invocation's cidfile.
    """
    scratch_location = common.get_scratch_location()
    cidfile_fpath = os.path.join(scratch_location, f"_docker_id_{''.join(random.choices(string.ascii_letters, k=12))}.txt")
    return cidfile_fpath

def _read_docker_id_from_cidfile(fpath):
    """
    Return the Docker ID from the given CIDfile, or None if the container ID isn't
    in there (yet).

    The Docker CLI creates the cidfile as soon as `docker run` starts, but only fills
    it in once the daemon has actually created the container - and removes it again if
    the container could not be created. So a missing or empty cidfile just means
    "no container ID available", not "something went wrong".
    """
    try:
        with open(fpath) as f:
            return f.read().strip() or None
    except FileNotFoundError:
        return None

def _get_docker_id_from_cidfile(fpath):
    """
    Return the Docker ID from the given CIDfile.
    """
    docker_id = _read_docker_id_from_cidfile(fpath)
    if not docker_id:
        raise OSError(f"Docker ID not found in CID file {fpath}")
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
        cacheargs = _get_registry_cache_args(args, docker_image_name, platform)
        builderargs = ""
        if getattr(args, 'docker_repo', None) is None and _get_buildx_driver() != "docker":
            # Without a registry, FROM references to locally-built base images can only be
            # resolved by a 'docker' driver builder (which shares the host image store);
            # container-driver builders try (and fail) to pull them from a registry instead.
            builder = _get_local_builder_name()
            common.info(f"No docker repo configured: using the '{builder}' buildx builder so locally-built base images can be found.")
            builderargs = f" --builder {builder}"
        dockercmd = f"docker buildx build{builderargs} --sbom=false --provenance=false --load --platform {platform} -f {dockerfile_name} {dockerargs}{cacheargs} -t {str(docker_image_name)} {context}"
    else:
        dockercmd = f"docker build -f {dockerfile_name} {dockerargs} -t {str(docker_image_name)} {context}"
    _run_build_command_with_retries(dockercmd, builddpath, docker_image_name)

    # Push the Docker image to the chosen repo (if given)
    if args.docker_repo is not None:
        push_docker_image(args, docker_image_name)

    return docker_image_name

def _get_buildx_driver() -> str:
    """
    Returns the driver name of the currently selected buildx builder
    ('docker', 'docker-container', etc.), or '' if it can't be determined.
    """
    global _BUILDX_DRIVER
    if _BUILDX_DRIVER is None:
        driver = ""
        p = subprocess.run("docker buildx inspect".split(), capture_output=True, encoding='utf-8')
        if p.returncode == 0:
            for line in p.stdout.splitlines():
                if line.strip().startswith("Driver:"):
                    driver = line.split(":", 1)[1].strip()
                    break
        _BUILDX_DRIVER = driver
    return _BUILDX_DRIVER

def _get_local_builder_name() -> str:
    """
    Returns the name of the buildx builder that uses the 'docker' driver for the current
    Docker context. That builder shares the host's local image store, so it can resolve
    FROM references to locally-built images. The builder is named after the current
    context; fall back to 'default' if we can't determine it.
    """
    p = subprocess.run("docker context show".split(), capture_output=True, encoding='utf-8')
    if p.returncode == 0 and p.stdout.strip():
        return p.stdout.strip()
    return "default"

def _get_registry_cache_args(args, docker_image_name: DockerImageName, platform: str) -> str:
    """
    Returns --cache-from/--cache-to arguments for a buildx build, using a per-image,
    per-architecture cache manifest stored in the configured Docker repo. This is what
    lets fresh CI machines reuse layers from previous pipelines; it composes with
    --force-build, which only bypasses the task-level (whole-image) cache.
    """
    if getattr(args, 'docker_repo', None) is None or args.docker_no_cache:
        return ""

    arch = platform.split('/')[-1]
    cacheref = f"{docker_image_name.repo}{docker_image_name.name}:buildcache-{arch}"
    cacheargs = f" --cache-from type=registry,ref={cacheref}"
    if _get_buildx_driver() == "docker":
        # The default 'docker' driver can import a registry cache but cannot export one.
        common.info("Buildx is using the default 'docker' driver, which does not support cache export. Using --cache-from only.")
    else:
        cacheargs += f" --cache-to type=registry,ref={cacheref},mode=max"
    return cacheargs

def _run_build_command_with_retries(dockercmd: str, builddpath: str, docker_image_name: DockerImageName, nretries=BUILD_NRETRIES):
    """
    Run the given docker build command, retrying on failure. Build failures are often
    transient (registry pulls, apt/pip/git fetches inside the build), and Docker's
    layer cache lets a retry resume from the layer that failed.
    """
    for attempt in range(1, nretries + 1):
        common.info(f"Running: {dockercmd}")
        p = subprocess.run(dockercmd.split(), cwd=builddpath)
        if p.returncode == 0:
            return
        if attempt < nretries:
            delay_s = 2 ** attempt
            common.warning(f"Docker build of {docker_image_name} failed with return code {p.returncode} (attempt {attempt}/{nretries}). Retrying in {delay_s}s...")
            time.sleep(delay_s)
    p.check_returncode()

def get_host_architecture() -> str:
    """
    Returns the architecture of the Docker server ('amd64', 'arm64', ...), or '' if
    it can't be determined. Containers can only be run from images built for this
    architecture (barring emulation).
    """
    global _HOST_ARCH
    if _HOST_ARCH is None:
        p = subprocess.run(["docker", "version", "--format", "{{.Server.Arch}}"], capture_output=True, encoding='utf-8')
        _HOST_ARCH = p.stdout.strip() if p.returncode == 0 else ""
    return _HOST_ARCH

def get_local_image_architecture(image_name: str|DockerImageName) -> str:
    """
    Returns the architecture of the given image as it exists in the local image store
    ('amd64', 'arm64', ...), or '' if the image cannot be found locally.
    """
    p = subprocess.run(["docker", "image", "inspect", str(image_name), "--format", "{{.Architecture}}"], capture_output=True, encoding='utf-8')
    return p.stdout.strip() if p.returncode == 0 else ""

def tag_docker_image(source: str|DockerImageName, target: str|DockerImageName):
    """
    Add `target` as an additional local tag for the image `source`, which must already
    be present in the local image store.
    """
    cmd = ["docker", "tag", str(source), str(target)]
    common.info(f"Running command: {' '.join(cmd)}")
    p = subprocess.run(cmd, capture_output=True, encoding='utf-8')
    if p.returncode != 0:
        msg = f"Failed to tag {source} as {target}: {p.stderr.strip()}"
        common.error(msg)
        raise RuntimeError(msg)

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
        # Get the docker ID. It may not be in there, in which case there's no container to stop.
        docker_id = _read_docker_id_from_cidfile(cidfile_fpath)
        if not docker_id:
            continue
        short_id = docker_id[:8]

        # Stop the container
        common.info(f"Sending stop signal to container {short_id}...")
        stop_docker_container(docker_id)

def parse_docker_image_name(fully_qualified_name: str):
    """
    Returns a DockerImageName object from a fully-qualified str version of a Docker image.

    This differs from `construct_docker_image_name` in that it takes a string of the form

    'artiehub:5000/artie-api-server:f933906-amd64' or similar and returns a DockerImageName object
    with the constituent pieces parsed out.

    construct_docker_image_name on the other hand, takes the constituent pieces already parsed,
    infers ones that aren't given, and returns the DockerImageName object from these pieces.
    """
    # Thank you, Stack Overflow: https://stackoverflow.com/questions/74990220/how-to-use-docker-image-tag-parsing-regex-in-javascript
    # With a minor modification
    r = re.compile(r"^(?P<repository>[\w.\-_]+(?::\d+|)|)(?:/|)(?P<image>[a-z0-9.\-_]+(?:/[a-z0-9.\-_]+|))(:(?P<tag>[\w.\-_]{1,127})|)$")
    o = r.match(fully_qualified_name)
    if not o:
        errmsg = f"Could not understand the given string as a Docker image ID: {fully_qualified_name}"
        common.error(errmsg)
        raise ValueError(errmsg)
    return DockerImageName(o.groupdict().get('repository', ""), o.groupdict().get('image', ""), o.groupdict().get('tag', ""))

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

def annotate_manifest(manifest_name: str, docker_image_names: List[str|DockerImageName]):
    """
    Annotate the given manifest with the proper architecture information.
    """
    for image_name in docker_image_names:
        tag = get_tag_from_name(image_name)
        if tag.endswith("-arm64"):
            arch = "arm64"
        elif tag.endswith("-amd64"):
            arch = "amd64"
        else:
            msg = f"Cannot determine architecture from tag {tag} of image {image_name} when annotating manifest {manifest_name}."
            common.error(msg)
            raise ValueError(msg)

        cmd = ["docker", "manifest", "annotate", manifest_name, str(image_name), "--arch", arch]
        common.info(f"Running command: {' '.join(cmd)}")
        p = subprocess.run(cmd, capture_output=True)
        if p.returncode != 0:
            common.error(f"Failed to run cmd: {cmd}")
            common.error(f"Subprocess's stderr: {p.stderr.decode('utf-8')}")
            common.error(f"Subprocess's stdout: {p.stdout.decode('utf-8')}")
            p.check_returncode()

def create_manifest(manifest_name: str, docker_image_names: List[str|DockerImageName], insecure=False) -> DockerManifest:
    """
    Create a Docker Manifest on the host file system and return an object representing it.
    """
    images = [str(name) for name in docker_image_names]
    manifest = DockerManifest(manifest_name, images, insecure)

    # Create the manifest on the host system. This is currently experimental, so we just use a subprocess.
    cmd = ["docker", "manifest", "create"]

    if manifest.insecure:
        cmd.append("--insecure")

    cmd.append(manifest.name)

    for image in manifest.image_names:
        cmd.append(image)

    p = subprocess.run(cmd, capture_output=True)
    if p.returncode != 0:
        common.error(f"Failed to run cmd: {cmd}")
        common.error(f"Subprocess's stderr: {p.stderr.decode('utf-8')}")
        common.error(f"Subprocess's stdout: {p.stdout.decode('utf-8')}")
        p.check_returncode()

    return manifest

def create_and_push_manifest_via_imagetools(manifest_name: str, docker_image_names: List[str|DockerImageName], nretries=3):
    """
    Create and push a multi-arch manifest list in a single step using
    'docker buildx imagetools create'. All of the constituent images must already
    have been pushed to the registry; nothing needs to be present locally.
    """
    cmd = ["docker", "buildx", "imagetools", "create", "-t", manifest_name] + [str(name) for name in docker_image_names]
    common.info(f"Running command: {' '.join(cmd)}")
    for attempt in range(1, nretries + 1):
        p = subprocess.run(cmd, capture_output=True)
        if p.returncode == 0:
            return
        common.warning(f"Failed to create/push manifest {manifest_name} (attempt {attempt}/{nretries}): {p.stderr.decode('utf-8')}")
        if attempt < nretries:
            time.sleep(2)
    common.error(f"Failed to run cmd: {cmd}")
    common.error(f"Subprocess's stderr: {p.stderr.decode('utf-8')}")
    common.error(f"Subprocess's stdout: {p.stdout.decode('utf-8')}")
    p.check_returncode()

def push_manifest(manifest: DockerManifest):
    """
    Push the given manifest.
    """
    cmd = ["docker", "manifest", "push"]

    if manifest.insecure:
        cmd.append("--insecure")

    cmd.append(manifest.name)

    p = subprocess.run(cmd, capture_output=True)
    if p.returncode != 0:
        common.error(f"Failed to run cmd: {cmd}")
        common.error(f"Subprocess's stderr: {p.stderr.decode('utf-8')}")
        common.error(f"Subprocess's stdout: {p.stdout.decode('utf-8')}")
        p.check_returncode()

def remove_manifest(manifest_name: str, fail_ok=False) -> None:
    """
    Remove the manifest with the given name. Raises a CalledProcessError if the manifest cannot be found.
    """
    p = subprocess.run(["docker", "manifest", "rm", manifest_name], capture_output=True, encoding='utf-8')
    if fail_ok and p.returncode != 0:
        common.info(f"Could not remove manifest {manifest_name}. This may be normal.")
    elif not fail_ok:
        p.check_returncode()

def get_tag_from_name(docker_image_name: str|DockerImageName) -> str:
    """
    Returns the tag name of the docker image.
    """
    if issubclass(type(docker_image_name), DockerImageName):
        return docker_image_name.tag
    else:
        return parse_docker_image_name(docker_image_name).tag

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
    pattern_name = re.compile(r"\"Name\":\"(?P<name>)\"")
    # Example: "ID":"791e54dd426b"
    pattern_id = re.compile(r"\"ID\":\"(?P<id>)\"")
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
    p = subprocess.Popen(["docker", "run", "--rm", "--cidfile", cidfile_fpath, image], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    # Wait for the container to start up (i.e., for the Docker CLI to write the container
    # ID into its cidfile), but don't keep waiting if 'docker run' has already exited -
    # that means it never started. Note that we have to wait for the cidfile to have
    # *contents*: the CLI creates it empty up front and only fills it in once the daemon
    # has created the container, which can take a while when the daemon is busy building
    # a bunch of images in parallel.
    started_at = time.time()
    while True:
        docker_id = _read_docker_id_from_cidfile(cidfile_fpath)
        if docker_id:
            break
        if p.poll() is not None:
            stderr = p.stderr.read().decode('utf-8').strip() if p.stderr else ""
            msg = f"Could not start a container from image {image} (docker run exited with {p.returncode}): {stderr}"
            common.error(msg)
            raise RuntimeError(msg)
        if time.time() - started_at > CONTAINER_START_TIMEOUT_S:
            p.kill()
            msg = f"Timed out after {CONTAINER_START_TIMEOUT_S}s waiting for a container to start from image {image}."
            common.error(msg)
            raise TimeoutError(msg)
        time.sleep(0.1)

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
    if re.compile(r".+://.+").match(args.docker_repo):
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
        container.stop(timeout=10)
        container.reload()
        if container.status != "exited":
            common.warning(f"Container {container.name} did not stop successfully. Attempting to kill it.")
            container.kill()
            container.reload()
            if container.status != "exited":
                common.warning(f"Container {container.name} did not kill successfully. It may still be using the network, which may cause problems.")

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

def get_platform_from_name(docker_image_name: str|DockerImageName) -> str:
    """
    Returns the Docker platform ('linux/amd64', 'linux/arm64') implied by the image's
    tag suffix, or '' if the tag doesn't name an architecture. Per-arch images are tagged
    '<tag>-<arch>' by construct_docker_image_name().
    """
    tag = get_tag_from_name(docker_image_name)
    for arch in ("amd64", "arm64"):
        if tag.endswith(f"-{arch}"):
            return f"linux/{arch}"
    return ""

def _try_pull_once(docker_image_name: DockerImageName, client, platform=None):
    try:
        ret = client.api.pull(f"{docker_image_name.repo}{docker_image_name.name}", docker_image_name.tag, stream=True, decode=True, platform=platform if platform else None)
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

    # Per-arch images (tagged '<tag>-<arch>') must be pulled with an explicit platform, or
    # Docker will look for the host's architecture in them and fail on a foreign-arch image.
    platform = get_platform_from_name(imgname)

    client = docker.from_env(timeout=API_CALL_TIMEOUT_S)
    err = None
    for i in range(nretries):
        if i == 0:
            common.info(f"Pulling Docker image {imgname}{f' for platform {platform}' if platform else ''}...")
        else:
            common.warning(f"Pulling failed. Retrying {imgname}...")
            time.sleep(1)

        err = _try_pull_once(imgname, client, platform)
        if err is None:
            break

    if err is not None:
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

def remove_docker_image(docker_image_name: DockerImageName, fail_ok=False):
    """
    Removes the given Docker image from the local system.

    If `fail_ok` is True, we do not raise an exception if the image cannot be found.
    """
    client = docker.from_env(timeout=API_CALL_TIMEOUT_S)
    try:
        client.images.remove(str(docker_image_name), force=True)
    except docker_errors.ImageNotFound:
        if not fail_ok:
            raise

def run_docker_container(image_name, cmd: str|None, timeout_s=30, log_to_stdout=False, **kwargs):
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
    runner = DockerRunner(client, image=image_name, cmd=cmd, **kwargs)
    common.manage_timeout(runner, timeout_s)
    stdout = runner.get_container_output()

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

def start_docker_container(image_name: str|DockerImageName, cmd: str|None, remove=True, **kwargs):
    """
    Starts a Docker container with the given command executed inside the container
    and returns a `Container` object from the `docker` package after detaching from it.

    Args
    ----
    - image_name: The name of the Docker image to run as a container
    - cmd: The command to run inside the Docker container
    - log_to_stdout: If given, we log the Docker logs to the console.
    - remove: If `True`, we remove the container after it exits.
    - kwargs: Keyword arguments for docker.run() command. See https://docker-py.readthedocs.io/en/stable/containers.html#docker.models.containers.ContainerCollection.run
    """
    client = docker.from_env(timeout=API_CALL_TIMEOUT_S)
    common.info(f"Running command: {cmd}")
    container = client.containers.run(str(image_name), cmd, remove=remove, detach=True, **kwargs)
    return container

def wait_for_container_to_exit(container, timeout_s: float, poll_interval_s=1.0) -> bool:
    """
    Block until the given container has stopped running, or until `timeout_s` has elapsed.

    Returns `True` if the container is done running (or is already gone), `False` if we
    gave up waiting on it.

    Args
    ----
    - container: A `Container` object from the `docker` package, such as `start_docker_container()` returns.
    - timeout_s: How long (in seconds) to wait for the container before giving up.
    - poll_interval_s: How long (in seconds) to wait between checks of the container's status.
    """
    started_at = time.time()
    while time.time() - started_at < timeout_s:
        try:
            container.reload()
        except docker_errors.NotFound:
            # The container has exited and has already been cleaned up
            return True

        if container.status not in ("created", "running"):
            return True

        time.sleep(poll_interval_s)

    return False
