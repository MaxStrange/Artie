from setuptools import setup
setup(
    name='artie-tooling',
    version="0.0.1",
    python_requires=">=3.10",
    license="MIT",
    packages=[
        "artie_tooling",
        "artie_tooling.api_clients",
    ],
    package_dir={
        "artie_tooling": "src/artie_tooling",
        "artie_tooling.api_clients": "src/artie_tooling/api_clients",
    },
    install_requires=[
        "pyyaml>=6.0"
    ]
)
