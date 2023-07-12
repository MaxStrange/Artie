from setuptools import setup
setup(
    name='artiecli',
    version="0.0.1",
    python_requires=">=3.10,<3.12",
    license="MIT",
    install_requires=[
        "rpyc==5.3.1",
        "requests<2.29.0",
        "kubernetes==28.*"
    ],
    packages=["artiecli", "artiecli.modules"],
    entry_points={
        'console_scripts': [
            "artie-cli = artiecli.cli:main"
        ]
    }
)
