# !/usr/bin/env python
# coding=utf-8

from setuptools import setup, find_packages

# python setup.py bdist_wheel
setup(
    name="mindx_training_toolkit",
    version="1.0.0",
    packages=find_packages(),
    zip_safe=False,
    python_requires=">=3.7.5",
    include_package_data=True,
    entry_points={
        "console_scripts": ["training-toolkit=training_toolkit.main:main"],
    }
)