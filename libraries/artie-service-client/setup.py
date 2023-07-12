from setuptools import setup
setup(
    name='artie-service-client',
    version="0.0.1",
    python_requires=">=3.10",
    license="MIT",
    packages=["artie_service_client"],
    package_dir={"artie_service_client": "src/artie_service_client"},
    install_requires=[
        "artie-util",
        "rpyc==5.3.1",
    ]
)
