from setuptools import setup
setup(
    name='artie-gpio',
    version="0.0.1",
    python_requires=">=3.10",
    license="MIT",
    packages=["artie_gpio"],
    package_dir={"artie_gpio": "src/artie_gpio"},
    install_requires=[
        "artie-util",
        "RPi.GPIO",
    ],
)
