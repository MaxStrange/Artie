"""
All packaging metadata lives in pyproject.toml. This file exists only to pass `cffi_modules` to
setuptools, which is a keyword contributed by cffi's setuptools plugin and so has no declarative
equivalent in pyproject.toml. It points at the FFI builder in build_ffi.py, which compiles the C
library and the generated bindings into artie_can._artie_can at install time.
"""
from setuptools import setup

setup(cffi_modules=["build_ffi.py:ffibuilder"])
