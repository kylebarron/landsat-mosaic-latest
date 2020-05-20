"""Setup landsat-mosaic-latest."""

from setuptools import find_packages, setup

setup_reqs = ['setuptools >= 38.6.0', 'twine >= 1.11.0']

with open('README.md') as f:
    readme = f.read()

# Runtime requirements.
inst_reqs = ["boto3"]

extra_reqs = {
    "test": ["pytest", "pytest-cov", "mock"],
    "dev": ["pytest", "pytest-cov", "pre-commit", "mock"]}

setup(
    name="landsat-mosaic-latest",
    version="0.1.0",
    description="Auto-updating cloudless Landsat mosaic from SNS notifications",
    long_description=readme,
    long_description_content_type='text/markdown',
    python_requires=">=3.6",
    classifiers=[
        "Intended Audience :: Information Technology",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7", ],
    keywords="COG COGEO Mosaic GIS Landsat",
    author="Kyle Barron",
    author_email="kylebarron2@gmail.com",
    url="https://github.com/kylebarron/landsat-mosaic-latest",
    license="MIT",
    packages=find_packages(exclude=["ez_setup", "examples", "tests"]),
    include_package_data=True,
    zip_safe=False,
    install_requires=inst_reqs,
    setup_requires=setup_reqs,
    extras_require=extra_reqs,
)
