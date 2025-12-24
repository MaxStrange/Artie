# This is required for now because Yocto cannot understand pyproject.toml
# See https://setuptools.pypa.io/en/latest/references/keywords.html for legacy syntax
from setuptools import setup
setup(
    name='artiecli',
    version="0.0.1",
    python_requires=">=3.10,<3.12",
    license="MIT",
    install_requires=[
        "requests<2.29.0",
        "urllib3<2.0.0",
        "artie-tooling>=0.0.1",
    ],
    extras_require={
        "remote": [
            "rpyc==5.3.1",
        ],
    },
    packages=["artiecli", "artiecli.modules"],
    entry_points={
        'console_scripts': [
            "artie-cli = artiecli.cli:main"
        ]
    }
)
