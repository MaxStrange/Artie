"""
This module contains code for doing ArtieTool stuff.
"""
from workbench.comms import base
from workbench.util import log
from artie_tooling import artie_profile
from artie_tooling import hw_config
import datetime
import json
import subprocess
import sys

# Command prefix used to invoke Artie Tool.
#
# artietool is a declared dependency of Workbench, so it is always importable from the
# environment Workbench itself is running in. Invoking it via that same interpreter is
# therefore guaranteed to find it, and works equally well for a pip install and for an
# editable checkout. Deliberately not a PATH lookup for `artie-tool`: PATH could resolve
# to a console script belonging to some other environment, with a different Artie Tool
# version than the one Workbench was installed against.
ARTIE_TOOL_CMD = [sys.executable, "-m", "artietool.cli"]

class ArtieToolInvoker(base.ArtieCommsBase):
    """
    Class for invoking ArtieTool commands asyncronously,
    allowing for reading out the live output at the same time.
    """
    def __init__(self, config: artie_profile.ArtieProfile, logging_handler=None):
        super().__init__(logging_handler)
        self.config = config
        self._process = None
        self._retcode = None

    @property
    def success(self) -> bool:
        """Returns True if the subprocess completed successfully."""
        return self._retcode == 0

    def open(self):
        """No-op for ArtieToolInvoker."""
        super().open()

    def close(self):
        """Terminate the subprocess if it's still running."""
        if self._process and self._process.poll() is None:
            self._process.terminate()
            self._process.wait()

        super().close()

    def deploy(self, configuration: str) -> Exception|None:
        """Run the deploy command asynchronously, returning an error if something goes wrong launching it."""
        cmd = ARTIE_TOOL_CMD + [
            "deploy",
            configuration
        ]
        log.debug(f"Running command: {str(cmd)}")
        return self._run_cmd(cmd)

    def get_hw_config(self) -> tuple[Exception|None, hw_config.HWConfig|None]:
        """Get hardware configuration synchronously, returning an error if something goes wrong."""
        cmd = ARTIE_TOOL_CMD + [
            "get",
            "hw-config",
            "--json"
        ]
        log.debug(f"Running command: {str(cmd)}")
        err, data, stderr = self._run_cmd_blocking(cmd, json_output=True)
        if err:
            return (err, None)

        try:
            artie_hw_config = hw_config.HWConfig.from_json(data)
        except json.JSONDecodeError as e:
            return (e, None)

        return artie_hw_config

    def install(self, hw_config_fpath: str) -> Exception|None:
        """Run the install command asynchronously, returning an error if something goes wrong launching it."""
        cmd = ARTIE_TOOL_CMD + [
            "install",
            "--username", self.config.credentials.username,
            "--artie-ip", self.config.controller_node_ip,
            "--admin-ip", self.config.k3s_info.admin_node_ip,
            "--artie-name", self.config.artie_name,
            "--artie-type-file", hw_config_fpath,
            "--password", self.config.credentials.password,
            "--token", self.config.k3s_info.token
        ]
        # TODO: When we require username/password, make sure to mask them in the logs
        #log.debug(f"Running command: {str(cmd)}".replace(self.config.credentials.password, "****").replace(self.config.k3s_info.token, "****"))
        log.debug(f"Running command: {str(cmd)}")
        return self._run_cmd(cmd)

    def join(self, timeout_s=None) -> tuple[Exception|None, bool]:
        """
        Wait until the subprocess finishes, then return. Optionally include a timeout.
        Returns a tuple of (error, success). If timeout occurs, error will be a TimeoutExpired exception.
        """
        deadline = datetime.datetime.now() + datetime.timedelta(seconds=timeout_s) if timeout_s else None
        while self._process and self._process.poll() is None:
            if deadline and datetime.datetime.now() >= deadline:
                return (subprocess.TimeoutExpired(self._process.args, timeout_s), False)

            if self._process.stdout:
                msg = self._process.stdout.readline().decode().strip()
                if msg:
                    log.info(msg)

            # If we get something on stderr, it means something went wrong, and we should read
            # the entire stdout first, then read out the stderr
            if self._process.stderr:
                err_msg = self._process.stderr.readline().decode().strip()
                if err_msg:
                    # Read remaining stdout
                    if self._process.stdout:
                        log.info(self._process.stdout.read().decode().strip())
                    err_msg += self._process.stderr.read().decode().strip()
                    log.error(err_msg)

        self._retcode = self._process.returncode
        return (None, self.success)

    def list_deployments(self) -> tuple[Exception|None, list[str]]:
        """List deployments, returning an error if something goes wrong, otherwise a list of deployment names."""
        cmd = ARTIE_TOOL_CMD + [
            "deploy",
            "list",
            "--loglevel", "error"
        ]
        log.debug(f"Running command: {str(cmd)}")
        err, stdout, _ = self._run_cmd_blocking(cmd)
        if err:
            return (err, [])

        return (None, stdout.strip().splitlines())

    def read(self) -> tuple[Exception|None, str, str]:
        """
        Read available output from the subprocess.
        Returns a tuple of (error, stdout, stderr).
        If no output is available, stdout and stderr will be empty strings.
        """
        if not self._process:
            return (RuntimeError("Process not started."), "", "")

        try:
            stdout_bytes = self._process.stdout.read(4096) if self._process.stdout else b""
            stderr_bytes = self._process.stderr.read(4096) if self._process.stderr else b""
            stdout = stdout_bytes.decode('utf-8', errors='replace')
            stderr = stderr_bytes.decode('utf-8', errors='replace')
            return (None, stdout, stderr)
        except Exception as e:
            return (e, "", "")

    def read_all(self, nbytes=256):
        """
        Read output from the subprocess until it completes, yielding
        a tuple of stdout, stderr of size up to nbytes at a time.
        If no output is available, stdout and stderr will be empty strings.
        """
        if not self._process:
            return "", ""

        while self._process.poll() is None:
            yield (self._process.stdout.read(nbytes).decode(), self._process.stderr.read(nbytes).decode())

        self._retcode = self._process.returncode

    def status_actuators(self, actuator: str = "all") -> tuple[Exception|None, dict|None]:
        """Get actuator status as JSON dict (see the artie-tool status API document), returning an error if something goes wrong."""
        cmd = ARTIE_TOOL_CMD + [
            "status",
            "actuators",
            "--actuator", actuator,
            "--json"
        ]
        log.debug(f"Running command: {str(cmd)}")
        err, stdout, stderr = self._run_cmd_blocking(cmd, json_output=True)
        if err:
            return (err, None)

        return (None, stdout)

    def status_mcus(self, mcu: str = "all") -> tuple[Exception|None, dict|None]:
        """Get MCU status as JSON dict (see the artie-tool status API document), returning an error if something goes wrong."""
        cmd = ARTIE_TOOL_CMD + [
            "status",
            "mcus",
            "--mcu", mcu,
            "--json"
        ]
        log.debug(f"Running command: {str(cmd)}")
        err, stdout, stderr = self._run_cmd_blocking(cmd)
        if err:
            return (err, None)

        return (None, stdout)

    def status_nodes(self, node: str = "all") -> tuple[Exception|None, dict|None]:
        """Get node status as JSON dict (see the artie-tool status API document), returning an error if something goes wrong."""
        cmd = ARTIE_TOOL_CMD + [
            "status",
            "nodes",
            "--node", node,
            "--json"
        ]
        log.debug(f"Running command: {str(cmd)}")
        err, stdout, stderr = self._run_cmd_blocking(cmd)
        if err:
            return (err, None)

        return (None, stdout)

    def status_pods(self, pod: str = "all") -> tuple[Exception|None, dict|None]:
        """Get pod status as JSON dict (see the artie-tool status API document), returning an error if something goes wrong."""
        cmd = ARTIE_TOOL_CMD + [
            "status",
            "pods",
            "--pod", pod,
            "--json"
        ]
        log.debug(f"Running command: {str(cmd)}")
        err, stdout, stderr = self._run_cmd_blocking(cmd)
        if err:
            return (err, None)

        return (None, stdout)

    def status_sensors(self, sensor: str = "all") -> tuple[Exception|None, dict|None]:
        """Get sensor status as JSON dict (see the artie-tool status API document), returning an error if something goes wrong."""
        cmd = ARTIE_TOOL_CMD + [
            "status",
            "sensors",
            "--sensor", sensor,
            "--json"
        ]
        log.debug(f"Running command: {str(cmd)}")
        err, stdout, stderr = self._run_cmd_blocking(cmd)
        if err:
            return (err, None)

        return (None, stdout)

    def test(self, test_type: str) -> Exception|None:
        """Run the test command asynchronously, returning an error if something goes wrong."""
        cmd = ARTIE_TOOL_CMD + [
            "test",
            test_type
        ]
        log.debug(f"Running command: {str(cmd)}")
        return self._run_cmd(cmd)

    def _run_cmd(self, cmd: list[str]) -> Exception|None:
        """Run the command in a subprocess asynchronously."""
        try:
            self._process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=False)
        except OSError as err:
            return err

    def _run_cmd_blocking(self, cmd: list[str], json_output: bool = False) -> tuple[Exception|None, str|dict, str]:
        """
        Run the command in a subprocess, blocking until it completes. Return an exception or None, stdout, and stderr.
        If the json_output flag is set, attempt to parse stdout as JSON and return the parsed object instead of raw string.
        """
        try:
            completed_process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            stdout = completed_process.stdout.decode('utf-8', errors='replace')
            stderr = completed_process.stderr.decode('utf-8', errors='replace')
            self._process = completed_process
            self._retcode = completed_process.returncode
            return (None, json.loads(stdout) if json_output else stdout, stderr)
        except OSError as err:
            return (err, "", "")
        except subprocess.CalledProcessError as err:
            stdout = err.stdout.decode('utf-8', errors='replace') if err.stdout else ""
            stderr = err.stderr.decode('utf-8', errors='replace') if err.stderr else ""
            self._process = None
            self._retcode = err.returncode
            return (err, stdout, stderr)
        except json.JSONDecodeError as e:
            return (e, stdout, stderr)
