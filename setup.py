from setuptools import find_packages, setup

setup(
    name='ivtools',
    version='1.0.0',
    description='package to automatize iv curves data taking and analysis',
    author='M',
    package_dir={"": "src"},
    packages=find_packages(where='src'),
    install_requires=['numpy']
)
