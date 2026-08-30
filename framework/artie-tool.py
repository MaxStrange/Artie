"""
Artie Tool is the build system, test harness, and release pipeline
for all the Artie software components.

Choose from one of the commands and try --help,
as in `python artie-tool.py test --help`

This script is a thin compatibility shim. The implementation now lives in the
`artietool` package, and the supported way to invoke it is the `artie-tool`
console script installed by `pip install artietool`. This file remains so that
existing CI jobs and developer habits keep working during the repo split.
"""
from artietool.cli import main

if __name__ == "__main__":
    main()
