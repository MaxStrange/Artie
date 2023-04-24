"""
Determines what Docker image is latest for each of the values
we need in the given compose file. Then prints to the console
the command you should invoke to launch that test manually.

Uses heuristics, conventions, traditions, superstitions, and just
all around bad practices to try its best.
"""
from typing import List
from typing import Tuple
import argparse
import datetime
import docker
import os
import re
import subprocess
import yaml

def get_dependency_names(fpath: str) -> List[str]:
    """
    Convert "${WHATEVER}" as found in 'image' sections in the YAML to "WHATEVER".
    """
    with open(fpath, 'r') as f:
        docker_compose = yaml.safe_load(f)

    dependencies = []
    exp = re.compile("\$\{.+\}")
    services = [k for k in docker_compose['services'].keys()]
    for service in services:
        service_def = docker_compose['services'][service]
        if 'image' in service_def and exp.match(service_def['image'].strip()):
            image_name = service_def['image'].strip().rstrip("}").lstrip("${")
            dependencies.append(image_name)
    return dependencies

def retrieve_latest_docker_image(name: str) -> str:
    """
    Returns the latest Docker image that contains the given name.
    """
    try:
        subprocess.run("docker --help".split(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).check_returncode()
    except subprocess.CalledProcessError:
        print("Docker doesn't seem to be running. Start it up before running this script.")
        exit(2)

    matches = []
    client = docker.from_env()
    images = client.images.list(all=True)
    for image in images:
        for rt in image.attrs['RepoTags']:
            if name in rt:
                matches.append(image)

    if not matches:
        print(f"Couldn't find a Docker image that has been built that contains the name {name}")
        exit(3)

    matches = sorted(matches, key=lambda x: datetime.datetime.strptime(x.attrs['Created'][:-4], "%Y-%m-%dT%H:%M:%S.%f"))
    return [tag for tag in matches[-1].tags if name in tag][0]

def determine_image_dependencies(fpath: str) -> List[str]:
    """
    Return the required env variables and their values from the YAML file.
    """
    depnames = get_dependency_names(fpath)
    docker_images = []
    for depname in depnames:
        match depname:
            case "RESET_TEST_IMAGE":
                docker_images.append((depname, retrieve_latest_docker_image("artie-reset-driver")))
            case "EYEBROWS_TEST_IMAGE":
                docker_images.append((depname, retrieve_latest_docker_image("artie-eyebrow-driver")))
            case "MOUTH_TEST_IMAGE":
                docker_images.append((depname, retrieve_latest_docker_image("artie-mouth-driver")))
            case "LOG_COLLECTOR_TEST_IMAGE":
                docker_images.append((depname, retrieve_latest_docker_image("artie-log-collector")))
            case "METRICS_COLLECTOR_TEST_IMAGE":
                docker_images.append((depname, retrieve_latest_docker_image("artie-metrics-collector")))
            case _:
                print(f"Unrecognized value for a dependant image. Program me! {depname}")
                exit(1)
    return docker_images

def print_compose_command(deps: List[Tuple[str, str]], fpath: str):
    s = ""
    for env_var, value in deps:
        if os.name == 'nt':
            s += f'$Env:{env_var}="{value}"' + os.linesep
        else:
            s += f"export {env_var}={value}"
    s += f"docker compose -f {fpath} up --abort-on-container-exit --attach --always-recreate-deps --attach-dependencies --force-recreate --remove-orphans --renew-anon-volumes"
    print(s)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("compose_file", type=str, help="Compose file to launch.")
    args = parser.parse_args()

    if not os.path.isfile(args.compose_file):
        print("Can't find", args.compose_file)
        print("This script should be launched from its directory.")
        exit(-1)

    image_dependencies = determine_image_dependencies(args.compose_file)
    print_compose_command(image_dependencies, args.compose_file)
