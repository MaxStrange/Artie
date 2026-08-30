from typing import Dict
from typing import List
from typing import Tuple
from . import dependency
from . import result
from . import test_job
from . import single_container_cli_suite_job
from .. import common
from .. import workspace
from .. import docker
import datetime
import os
import yaml

class DockerComposeTestSuiteJob(test_job.TestJob):
    def __init__(self, steps: List[single_container_cli_suite_job.CLITest], compose_fname: str, compose_docker_image_variables: List[Tuple[str, str|dependency.Dependency]], docker_network_name: str) -> None:
        super().__init__(artifacts=[], steps=steps)
        self.compose_fname = compose_fname
        self.compose_variables = compose_docker_image_variables  # List of (key, value) pairs; gets transformed into dict[str: str] when setup() is called
        # Compose files ship with Artie Tool itself, so resolve them through the
        # component rather than assuming Artie Tool sits inside a larger tree.
        self.compose_dpath = os.path.join(workspace.repo_path("artietool"), "compose-files")
        self.docker_network_name = docker_network_name
        self.project_name = os.path.splitext(self.compose_fname)[0].replace('.', '-')
        self._dut_pids = {}

    def _set_compose_variables(self, args):
        compose_variables = {}
        for k, v in self.compose_variables:
            if issubclass(type(v), dependency.Dependency):
                compose_variables[k] = v.evaluate(args).item
            else:
                compose_variables[k] = v
        self.compose_variables = compose_variables

    def _extract_cli_environment_from_compose(self) -> Dict[str, str]:
        """
        Extract environment variables from the compose file that should be passed to CLI containers.
        Looks for common Artie environment variables in any service and extracts them.
        """
        compose_fpath = os.path.join(self.compose_dpath, self.compose_fname)
        if not os.path.exists(compose_fpath):
            common.warning(f"Compose file {compose_fpath} not found, cannot extract environment variables")
            return {}

        try:
            with open(compose_fpath, 'r') as f:
                compose_config = yaml.safe_load(f)
        except Exception as e:
            common.warning(f"Failed to parse compose file {compose_fpath}: {e}")
            return {}

        # Environment variables we want to extract for CLI
        target_env_vars = [
            'ARTIE_PUBSUB_BROKER_HOSTNAME',
            'ARTIE_PUBSUB_BROKER_PORT',
            'ARTIE_PUBSUB_USE_SSL',
            'ARTIE_SERVICE_BROKER_HOSTNAME',
            'ARTIE_SERVICE_BROKER_PORT',
        ]

        extracted_env = {}

        # Look through all services to find the target environment variables
        services = compose_config.get('services', {})
        for service_name, service_config in services.items():
            env_list = service_config.get('environment', [])

            # Environment can be either a list or a dict
            if isinstance(env_list, list):
                for env_item in env_list:
                    if isinstance(env_item, str):
                        # Format: "KEY=VALUE"
                        if '=' in env_item:
                            key, value = env_item.split('=', 1)
                            if key in target_env_vars:
                                extracted_env[key] = value
                    elif isinstance(env_item, dict):
                        # Format: {KEY: VALUE}
                        for key, value in env_item.items():
                            if key in target_env_vars:
                                extracted_env[key] = str(value)
            elif isinstance(env_list, dict):
                for key, value in env_list.items():
                    if key in target_env_vars:
                        extracted_env[key] = str(value)

        if extracted_env:
            common.info(f"Extracted environment variables for CLI from compose file: {', '.join(extracted_env.keys())}")

        return extracted_env

    def _get_logs(self, container_id: str) -> str:
        """
        Fetch logs from a Docker container using its ID.
        """
        container = docker.get_container(container_id)
        if container is None:
            raise ValueError(f"Container with ID {container_id} not found when trying to fetch logs.")

        try:
            logs = container.logs()
        except docker.docker_errors.NotFound:
            raise ValueError(f"Container with ID {container_id} closed unexpectedly while reading its logs.")

        return logs.decode('utf-8')

    def log_failures(self, args):
        """
        If the test failed, fetch logs from the Docker containers to help with debugging.
        """
        common.info(f"Test failed, fetching logs from Docker containers for debugging...")

        # Make a directory inside the artifacts directory for this test to store the logs
        logs_dir = os.path.join(args.artifact_folder, "docker_logs")
        os.makedirs(logs_dir, exist_ok=True)
        for dut_name, pid in self._dut_pids.items():
            try:
                common.info(f"Fetching logs from {dut_name} (container ID: {pid})...")
                logs = self._get_logs(pid)
                timestamp = datetime.datetime.now().strftime("%y-%b-%d-%H.%M.%S")
                log_file_path = os.path.join(logs_dir, f"{timestamp}_{dut_name}_{pid}.log")
                with open(log_file_path, "w") as log_file:
                    log_file.write(logs)
                common.info(f"Logs from {dut_name} (container ID: {pid}) saved to {log_file_path}")
            except Exception as e:
                common.error(f"Error fetching logs from Docker container {dut_name} (container ID: {pid}): {e}")

    def clean(self, args):
        """
        Clean up any Docker containers created by this job. This runs even if the job failed during setup or execution.
        Honors args.skip_teardown.
        """
        super().clean(args)

        if hasattr(args, "skip_teardown") and args.skip_teardown:
            common.info(f"--skip-teardown detected. You will need to manually clean up the Docker containers.")
            return

        common.info(f"Cleaning up Docker compose containers for project {self.project_name}...")

        try:
            self._set_compose_variables(args)
            docker.compose_down(self.project_name, self.compose_dpath, self.compose_fname, envs=self.compose_variables)
        except Exception as e:
            common.error(f"Error during docker compose down. There may be leftover containers or networks: {e}")

        try:
            docker.remove_network(self.docker_network_name)
        except Exception as e:
            common.error(f"Error removing docker network {self.docker_network_name}; there may be leftover networks: {e}")

    def setup(self, args):
        """
        Set up the DUTs by using Docker compose.
        """
        super().setup(args)
        if not os.path.isdir(self.compose_dpath):
            raise FileNotFoundError(f"Cannot find compose-files directory at {self.compose_dpath}")

        docker.add_network(self.docker_network_name)
        self._set_compose_variables(args)
        self._dut_pids = docker.compose(self.project_name, self.compose_dpath, self.compose_fname, args.test_timeout_s, envs=self.compose_variables)

        # Extract environment variables from compose file and set them on all CLI tests
        cli_environment = self._extract_cli_environment_from_compose()
        for step in self.steps:
            step.link_pids_to_expected_outs(args, self._dut_pids)
            # Merge extracted environment with any existing environment in the test
            # Test-specific environment takes precedence
            step.environment = {**cli_environment, **step.environment}

    def teardown(self, args, results: list[result.TestResult]):
        """
        Shutdown any Docker containers still at large.
        """
        if args.skip_teardown:
            common.info(f"--skip-teardown detected. You will need to manually clean up the Docker containers.")
            return

        try:
            common.debug(f"Tearing down Docker compose project {self.project_name} with compose file {self.compose_fname} at {self.compose_dpath}...")
            if results and any(r.status.value == result.TestStatuses.FAIL.value for r in results):
                self.log_failures(args)
            super().teardown(args, results)
            docker.compose_down(self.project_name, self.compose_dpath, self.compose_fname, envs=self.compose_variables)
            docker.remove_network(self.docker_network_name)
        except Exception as e:
            common.error(f"Error during teardown of Docker compose project {self.project_name}. You will likely have to manually clean up the Docker containers and network. Additionally, we cannot run further tests: {e}")
            raise e  # Reraise the exception so that we don't continue running more tests when the environment is likely still contaminated
