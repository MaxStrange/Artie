from setuptools import setup
setup(
    name='artie-service-client',
    version="0.0.1",
    python_requires=">=3.10",
    license="MIT",
    packages=[
        "artie_service_client",
        "artie_service_client.interfaces",
    ],
    package_dir={
        "artie_service_client": "src/artie_service_client",
        "artie_service_client.interfaces": "src/artie_service_client/interfaces",
    },
    install_requires=[
        "artie-util",
        "rpyc==6.0.1",
        # Imported directly at the top level of pubsub.py. Previously supplied only by the
        # Artie base image, so anything installing this package outside that image broke.
        "kafka-python==3.0.11",
    ]
)
