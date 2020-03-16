#!/usr/bin/env python
# -*- coding: utf-8 -*-
from setuptools import setup, find_packages
from os.path import dirname, join
from os import chdir

if dirname(__file__):
    chdir(dirname(__file__))

setup(
    name='doxypypy3',
    version='0.0.1',
    description='A Doxygen filter for Python',
    long_description=open(join(dirname(__file__), 'README.rst')).read(),
    keywords="Doxygen's input-filter of python language.",
    author='Eric W. Brown',
    url='https://github.com/625781186/doxypypy3',
    packages=find_packages(),
    test_suite='doxypypy3.test.test_doxypypy',
    entry_points={
        'console_scripts': [
            'doxypypy3 = doxypypy3.main:main'
        ]
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Environment :: Plugins',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Natural Language :: English',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: POSIX',
        'Operating System :: Unix',
        'Programming Language :: Python',
        'Topic :: Software Development :: Documentation'
    ],
    install_requires=[
        'icecream',
        'goto-statement',
    ],
)
