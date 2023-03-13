from setuptools import setup
setup(
    name='artie-i2c',
    version="0.0.1",
    python_requires=">=3.10",
    license="MIT",
    packages=["artie_i2c"],
    package_dir={"artie_i2c": "src/artie_i2c"},
    install_requires=[
        "smbus2",
    ]
)
