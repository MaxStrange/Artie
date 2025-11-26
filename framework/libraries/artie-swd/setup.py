from setuptools import setup
setup(
    name='artie-swd',
    version="0.0.1",
    python_requires=">=3.10",
    license="MIT",
    packages=["artie_swd"],
    package_dir={"artie_swd": "src/artie_swd"},
    install_requires=[
        "artie-util",
    ]
)
