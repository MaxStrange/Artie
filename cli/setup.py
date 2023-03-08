from setuptools import setup
setup(
    name='artiecli',
    version="0.0.1",
    python_requires=">=3.10",
    license="MIT",
    install_requires=[
        "artie-util",
        "artie-i2c",
        "RPi.GPIO",
        "zerorpc",
    ],
    entry_points={
        'console_scripts': [
            "artie-cli = artiecli.cli:main"
        ]
    }
)
