#!/usr/bin/env python3
"""
Runs the Artie CAN Python unit tests.

This is what the ``artie-can-python-unit-tests`` artie-tool task runs inside the test container,
and it is equally usable by hand::

    python run_tests.py                 # the whole suite
    python run_tests.py -k rpcacp       # anything pytest accepts is passed straight through

The task scrapes this container's output for one line per test, so the arguments below are not
cosmetic: ``-v`` is what makes pytest print a ``<test name> PASSED`` line for each test, and the
verdict line at the end is the suite-level guard that catches a run which dies part way through
after some tests have already passed.
"""
import sys
from pathlib import Path

import pytest

#: The Python suite. The sibling C suites (``tests/*.c`` and ``itest/``) are built and run by
#: CMake/CTest instead, so this deliberately points at one subdirectory rather than at ``tests/``.
TEST_DIR = Path(__file__).parent.resolve() / "tests" / "python"

#: What the artie-can-python-unit-tests task looks for to decide the suite as a whole was healthy.
PASS_LINE = "PYTEST SUITE:PASS"
FAIL_LINE = "PYTEST SUITE:FAIL"


def main(argv: list[str]) -> int:
    arguments = [str(TEST_DIR), "-v", "--tb=short", "-p", "no:cacheprovider", *argv]

    print(f"Running: pytest {' '.join(arguments)}\n", flush=True)
    exit_code = pytest.main(arguments)

    print(f"\n{PASS_LINE if exit_code == 0 else f'{FAIL_LINE} (pytest exit code {exit_code})'}",
          flush=True)
    return int(exit_code)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
