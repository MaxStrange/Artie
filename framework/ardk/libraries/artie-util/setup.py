from setuptools import setup
setup(
    name='artie-util',
    version="0.0.1",
    python_requires=">=3.10",
    license="MIT",
    packages=["artie_util"],
    package_dir={"artie_util": "src/artie_util"},
    install_requires=[
        "opentelemetry-api==1.17.0",
        "opentelemetry-sdk==1.17.0",
        "opentelemetry-exporter-otlp==1.17.0",
        "opentelemetry-exporter-prometheus==1.12.0rc1",
        # Imported directly by artie_logging.py. Left unpinned so the exporter above,
        # which also depends on it, remains the single source of the constraint.
        "prometheus_client",
        # Imported directly by util.py (ThreadPoolServer, SSLAuthenticator). Pinned to match
        # artie-service-client, which is what ends up installed today.
        "rpyc==6.0.1",
    ]
)
