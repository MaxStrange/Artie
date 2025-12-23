from setuptools import setup
setup(
    name='artie-tooling',
    version="0.0.1",
    python_requires=">=3.10",
    license="MIT",
    packages=["artie_tooling"],
    package_dir={"artie_tooling": "src/artie_tooling"},
    install_requires=[
        "pyyaml>=6.0"
    ]
)
