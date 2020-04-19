FROM lambci/lambda:build-python3.7

WORKDIR /tmp

ENV PYTHONUSERBASE=/var/task

COPY landsat_mosaic_latest/ landsat_mosaic_latest/
COPY setup.py setup.py
# Need to copy MANIFEST.in so that it correctly includes package data
COPY MANIFEST.in MANIFEST.in
COPY README.md README.md

# Install dependencies
RUN pip install . --user
RUN rm -rf landsat_mosaic_latest setup.py
