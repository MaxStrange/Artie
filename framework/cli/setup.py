# This is required for now because Yocto cannot understand pyproject.toml
# See https://setuptools.pypa.io/en/latest/references/keywords.html for legacy syntax
from setuptools import setup
setup(
    name='artiecli',
    version="0.0.1",
    python_requires=">=3.10",
    license="MIT",
    install_requires=[
        "urllib3<2.0.0",  # Kubernetes 28.1.0, which requires 1.24.2<=urllib3<=2.0
        "artie-tooling>=0.0.1",
        "artie-service-client>=0.0.1",
        "artie-util>=0.0.1",
        "artie-i2c>=0.0.1",
        "requests>=2.28.0",
        # cli.py imports every module in modules/ at import time, so modules/service.py's
        # top-level rpyc import is required for artie-cli to start at all - it is not optional.
        "rpyc==6.0.1",
    ],
    extras_require={
        # artie_can is a compiled extension that is not present in every environment
        # artie-cli runs in, so modules/can.py imports it lazily, per command.
        "can": [
            "artie-can>=0.1.0",
        ],
        # Retained for backwards compatibility: rpyc is now a hard dependency.
        "remote": [
            "rpyc==6.0.1",
        ],
    },
    packages=["artiecli", "artiecli.modules"],
    entry_points={
        'console_scripts': [
            "artie-cli = artiecli.cli:main"
        ]
    }
)
