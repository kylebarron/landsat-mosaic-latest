"""Setup landsat-mosaic-latest."""

from setuptools import find_packages, setup

# Runtime requirements.
inst_reqs = ["boto3"]

extra_reqs = {
    "test": ["pytest", "pytest-cov", "mock"],
    "dev": ["pytest", "pytest-cov", "pre-commit", "mock"],
    "script": ["click", "mercantile", "geopandas", "shapely"]}

setup(
    name="landsat-mosaic-latest",
    version="0.1.0",
    description="Auto-updating cloudless Landsat mosaic from SNS notifications",
    long_description=u"Create Cloud Optimized GeoTIFF mosaicsJSON.",
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
    extras_require=extra_reqs,
    entry_points={
        "console_scripts": [
            "landsat-mosaic-latest = landsat_mosaic_latest.scripts.cli:main"]},
)
