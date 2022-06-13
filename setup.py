
from setuptools import setup, find_packages

setup(
    name='tsutils',
    version=0.3,
    description='Utility bindings for The Syllabus codebase',
    author='The Syllabus',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'requests',
        'selenium-wire',
        'packaging',
        'lxml',
        'undetected-chromedriver>=3.1.5r4',
        'cloudscraper',
        ]
)