from setuptools import setup
setup(
    name='artie-driver-client',
    version="0.0.1",
    python_requires=">=3.10",
    license="MIT",
    packages=["artie_driver_client"],
    package_dir={"artie_driver_client": "src/artie_driver_client"},
    install_requires=[
        "artie-util",
        "rpyc==5.3.1",
    ]
)
