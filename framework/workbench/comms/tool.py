"""
This module contains code for doing ArtieTool stuff.
"""
import subprocess
from model import artie_profile

class ArtieToolInvoker:
    """
    Class for invoking ArtieTool commands asyncronously,
    allowing for reading out the live output at the same time.
    """
    def __init__(self, config: artie_profile.ArtieProfile):
        self.config = config
        self._process = None
        self._retcode = None

    @property
    def success(self) -> bool:
        """Returns True if the subprocess completed successfully."""
        return self._retcode == 0

    def deploy(self, configuration: str) -> Exception|None:
        """Run the deploy command, returning an error if something goes wrong."""
        cmd = [
            "python",
            "artie-tool.py",
            "deploy",
            configuration
        ]
        return self._run_cmd(cmd)

    def install(self) -> Exception|None:
        """Run the install command, returning an error if something goes wrong."""
        cmd = [
            "python",
            "artie-tool.py",
            "install",
            "--username", self.config.username,
            "--artie-ip", self.config.controller_node_ip,
            "--admin-ip", self.config.admin_node_ip,
            "--artie-name", self.config.artie_name
        ]
        return self._run_cmd(cmd)

    def join(self, timeout_s=None) -> Exception|None:
        """Wait until the subprocess finishes, then return. Optionally include a timeout."""
        try:
            self._process.wait(timeout=timeout_s)
            return None
        except subprocess.TimeoutExpired as e:
            return e

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
            yield self._process.stdout.read(nbytes).decode(), self._process.stderr.read(nbytes).decode()

        self._retcode = self._process.returncode

    def test(self, test_type: str) -> Exception|None:
        """Run the test command, returning an error if something goes wrong."""
        cmd = [
            "python",
            "artie-tool.py",
            "test",
            test_type
        ]
        return self._run_cmd(cmd)

    def _run_cmd(self, cmd: list[str]) -> Exception|None:
        """Run the command in a subprocess."""
        try:
            self._process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError as err:
            return err
