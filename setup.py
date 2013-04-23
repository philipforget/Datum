#!/usr/bin/env python

import os
import sys

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

if sys.argv[-1] == 'publish':
    os.system('python setup.py sdist upload')
    sys.exit()

packages = [
    'datum',
]

requires = ['pil']

setup(
    name='datum',
    version='0.1dev',
    description='Simply organize your images.',
    author='Philip Forget',
    author_email='philipforget@gmail.com',
    packages=packages,
    install_requires=requires,
    scripts = ['datum/bin/datum'],
)
