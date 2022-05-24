
from setuptools import setup, find_packages

setup(
    name='tsutils',
    version=0.1,
    description='Utility bindings for The Syllabus codebase',
    author='The Syllabus',
    packages=find_packages(),
    install_requires=[
        'requests',
        'selenium-wire',
        'packaging',
        'lxml',
        'undetected-chromedriver',
        'cloudscraper'
        ]
)