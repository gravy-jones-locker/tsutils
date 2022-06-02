
from setuptools import setup, find_packages

setup(
    name='tsutils',
    version=0.2,
    description='Utility bindings for The Syllabus codebase',
    author='The Syllabus',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'requests',
        'selenium-wire',
        'packaging',
        'lxml',
        'undetected-chromedriver',
        'cloudscraper',
        'selenium'
        ]
)