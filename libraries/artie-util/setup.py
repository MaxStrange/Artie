from setuptools import setup
setup(
    name='artie-util',
    version="0.0.1",
    python_requires=">=3.10",
    license="MIT",
    packages=["artie_util"],
    package_dir={"artie_util": "src/artie_util"},
    install_requires=[
        "opentelemetry-distro==0.38b0",
        "opentelemetry-exporter-otlp==1.17.0",
        "opentelemetry-exporter-prometheus==1.12.0rc1",
    ]
)
