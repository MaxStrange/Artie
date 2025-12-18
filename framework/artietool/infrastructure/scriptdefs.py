"""
This module contains definitions for script definitions used in tasks.
"""
from dataclasses import dataclass
from typing import List
from .. import common
import argparse
import subprocess

@dataclass
class ScriptDefinition:
    """
    A script definition, either inline or from a file.
    """
    script_path: str|None = None
    inline_script: str|None = None
    args: List[str]|None = None

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
            filled_arg = common.replace_variables(arg, args_obj)
            filled_args.append(filled_arg)
        
        self.args = filled_args

    def run_script(self, runtime_args: argparse.Namespace, *args, **kwargs) -> subprocess.CompletedProcess:
        """
        Runs the script defined by this `ScriptDefinition` by passing its contents to a shell,
        along with any other arguments provided. The given arguments should be appropriate for subprocess.run().

        First fills in the script definition with the provided runtime arguments via variable substitution.
        """
        if self.is_inline():
            cmd = common.replace_variables(self.inline_script, runtime_args)
        elif self.is_file():
            script_path = self.script_path
            cmd = [script_path] + [arg for arg in self.args] if self.args else [script_path]
        else:
            raise ValueError("ScriptDefinition must have either inline_script or script_path defined.")

        return subprocess.run(cmd, *args, **kwargs)
