"""
This module contains definitions for script definitions used in tasks.
"""
from dataclasses import dataclass
from typing import List
from .. import common
import argparse
import os
import subprocess
import tempfile

@dataclass
class ScriptDefinition:
    """
    A script definition, either inline or from a file.
    """
    script_path: str|None = None
    inline_script: str|None = None
    args: List[str|dict]|None = None

    def is_inline(self) -> bool:
        """
        Returns True if this script definition is an inline script.
        """
        return self.inline_script is not None

    def is_file(self) -> bool:
        """
        Returns True if this script definition is a script from a file.
        """
        return self.script_path is not None

    def fill_in_args(self, args_obj) -> None:
        """
        Fills in the arguments for this script definition using the provided args object.
        """
        if self.args is None:
            return

        filled_args = []
        for arg in self.args:
            if isinstance(arg, dict):
                for key, value in arg.items():
                    filled_key = common.replace_vars_in_string(key, args_obj)
                    filled_value = common.replace_vars_in_string(value, args_obj)
                    filled_args.append({filled_key: filled_value})
            else:
                filled_arg = common.replace_vars_in_string(arg, args_obj)
                filled_args.append(filled_arg)

        self.args = filled_args

    def run_script(self, runtime_args: argparse.Namespace, *args, **kwargs) -> subprocess.CompletedProcess:
        """
        Runs the script defined by this `ScriptDefinition` by passing its contents to a shell,
        along with any other arguments provided. The given arguments should be appropriate for subprocess.run().

        First fills in the script definition with the provided runtime arguments via variable substitution.
        """
        if self.is_inline():
            cmd = common.replace_vars_in_string(self.inline_script, runtime_args)
            return self._run_inline_script(cmd, *args, **kwargs)
        elif self.is_file():
            return self._run_file_script(self.script_path, *args, **kwargs)
        else:
            raise ValueError("ScriptDefinition must have either inline_script or script_path defined.")

    def _run_inline_script(self, script: str, *args, **kwargs) -> subprocess.CompletedProcess:
        """
        Run the inline script by writing it to a temporary file and executing it along with any args.
        """
        # Create a temporary file to hold the script
        with tempfile.NamedTemporaryFile(mode='w+', delete=True, delete_on_close=False, suffix='.sh') as temp_script:
            temp_script.write(script)
            temp_script.flush()
            temp_script.close()
            fpath = temp_script.name

            # Make the script executable
            os.chmod(fpath, 0o755)

            # Now run it
            return self._run_file_script(fpath, *args, **kwargs)

    def _run_file_script(self, fpath: str, *args, **kwargs) -> subprocess.CompletedProcess:
        """
        Run the script from file along with any potential args we have.
        """
        cmd = [fpath]

        if self.args:
            # Add positional args
            for arg in self.args:
                if not isinstance(arg, dict):
                    cmd.append(arg)
            # Add key:value args
            for arg in self.args:
                if isinstance(arg, dict):
                    for key, value in arg.items():
                        cmd.append(f"--{key}")
                        cmd.append(f"{value}")
        try:
            return subprocess.run(cmd, *args, **kwargs)
        except OSError:
            # Possibly the file needs to be run under a shell
            cmd = ['/bin/bash'] + cmd
            return subprocess.run(cmd, *args, **kwargs)
