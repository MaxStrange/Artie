from setuptools import setup
setup(
    name='artiecli',
    version="0.0.1",
    python_requires=">=3.10",
    license="MIT",
    install_requires=[
        "artie-i2c",
        "zerorpc",
    ],
    packages=["artiecli", "artiecli.modules"],
    entry_points={
        'console_scripts': [
            "artie-cli = artiecli.cli:main"
        ]
    }
)
