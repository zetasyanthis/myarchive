#!/usr/bin/env python3
# @Author: Zeta Syanthis <zetasyanthis>
# @Date:   2017/07/21
# @Email:  zeta@zetasyanthis.org
# @Project: MyArchive
# @Last modified by:   zetasyanthis
# @Last modified time: 2017/07/21
# @License MIT

from setuptools import setup, find_packages

setup(
    name="python-myarchive",
    version="0.0.1",
    description="A social media archiving tool.",
    author="Zeta Syanthis",
    author_email="zeta@zetasyanthis.org",
    url="https://github.com/zetasyanthis/myarchive",
    packages=find_packages("src/"),
    package_dir={'': 'src'},
    requires=['twitter',],
    test_requires=['tox', 'pytest', 'pylint', 'pep8']
)
