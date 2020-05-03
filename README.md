# landsat-mosaic-latest

Auto-updating cloudless Landsat 8 mosaic from AWS SNS notifications.

## Overview

AWS stores an [open, freely-accessible data
set](https://registry.opendata.aws/landsat-8/) of [Landsat
8](https://www.usgs.gov/land-resources/nli/landsat/landsat-8?qt-science_support_page_related_con=0#)
imagery. Crucially, this data is stored in [_Cloud-Optimized
GeoTIFF_](https://www.cogeo.org/) (COG), an extension of the GeoTIFF standard
which specifies a smart internal layout for image overviews. By reading the
image's header, an application can understand the byte ranges of different parts
of the image, and can read them using HTTP range requests without needing to
download the entire file.

This file type allows for new cloud-native processing models. For example, you
can serve a basemap of Landsat 8 imagery using serverless AWS Lambda functions.
This is a huge advance in technology because it allows for **serving satellite
imagery without needing to pregenerate and store any imagery**. This enables
huge cost savings, especially for hobby projects, where just storing hundreds of
GB or TB of data would be cost-prohibitive.

There exists an AWS Simple Notification Service (SNS)
[Topic](https://registry.opendata.aws/landsat-8/) that creates notifications
when new Landsat data are added to the AWS open data set. This library defines
an AWS Lambda function to run when those notifications are sent, and update a
DynamoDB database with identifiers for the most recent imagery per mercator tile
quadkey.

This library does not provide on-the-fly image tiling. For that, look at
[`awspds-mosaic`](https://github.com/developmentseed/awspds-mosaic).

Also note that this library creates a new DynamoDB table but does not populate
it with initial values. It only updates the table as new imagery comes in. To
create an inital Landsat mosaic, see
[`landsat-cogeo-mosaic`](https://github.com/kylebarron/landsat-cogeo-mosaic)
(note that the quadkey zoom must match; if you don't change the quadkey index
file below, you must create a mosaic with quadkey zoom 8). Then after the deploy
step below, upload the starting mosaic to the table.

## Install

```
git clone https://github.com/kylebarron/landsat-mosaic-latest
cd landsat-mosaic-latest
pip install .
```

### Create quadkey index file (optional)

**Unless you have specific requirements, you can skip this section.**

Landsat images are produced in a [grid of _paths_ and
_rows_](https://landsat.gsfc.nasa.gov/wp-content/uploads/2013/01/wrs2.gif). In
order to keep things simple and eliminate geospatial dependencies, this package
relies on a prebuilt index that associates those path-row combinations to the
mercator tile quadkeys used by the tiler.

By default, this library ships with a worldwide index at quadkey zoom level 8.
If you need a differing quadkey zoom or want to restrict your mosaic to a
geographic bounding box (not yet implemented), you can build your own index with
the following instructions.

There are a few additional dependencies needed to run this script. They aren't
included in the default requirements list to keep the lambda bundle as small as
possible. To install these, just run

```bash
pip install ".[script]"
```

Then to create the index, run:

```bash
landsat-mosaic-latest pathrow-index \
    --quadkey-zoom 8 \
    --gzip \
    --jsonl \
    data/path-row/WRS2_descending.shp \
    > landsat_mosaic_latest/data/index.jsonl.gz
```

In this example, a quadkey zoom of 8 is chosen, and the index is built for the
entire world.

Note it's currently imperative to copy the above line exactly, changing only the
`quadkey_zoom` argument. It must be created with `--gzip` and `--jsonl` and
placed into the designated location in order to be properly found during
runtime.

## Build

If you wish to change the quadkey index file, as described above, make sure you
do that before building, as that file will be included in the lambda bundle.

Then building is simple: (requires Docker and Make)

```bash
make package
```

This creates a `package.zip` file in the current directory with this package's
code and any required dependencies. This will be uploaded to AWS in the next
step.

## Deploy

To simplify deployment, this package uses the Serverless framework. [Refer to
their docs](https://serverless.com/framework/docs/getting-started/) to install
the `sls` command line library and authorize it with your AWS credentials.

Then it's simple to deploy this stack with a single line:

```bash
sls deploy --table-name landsat-auto-update --max-cloud-cover 5
```

- `table-name` is the name given to the DynamoDB table. You'll need to provide this information to the tiler when serving imagery.
- `max-cloud-cover` is an integer between 0 and 100 that defines the maximum percent cloud cover permitted for new imagery. If a new Landsat scene has cloud cover greater than the given percent, it will not be added to the DynamoDB table.

## Pricing

**\$2.64 per year** is a rough estimate of the cost to keep this DynamoDB table updated.

Note that actually serving imagery using a
[tiler](https://github.com/developmentseed/awspds-mosaic) is not included in
this estimate.

### Lambda

**Time**:

- \$ per 100ms: 0.0000016667 (when set to 1024mb memory. From a simple test, it looks like setting to lower memory doesn't reduce cost because it takes proportionally longer.)
- Rough # of 100ms when the scene is not cloudy: 10
- Percentage of time when scene is below max cloud cover: 0.3
- Scenes per day: [~750](https://www.usgs.gov/faqs/what-are-acquisition-schedules-landsat-satellites?qt-news_science_products=0#qt-news_science_products)
- Days per year: 365

Roughly \$1.36/year for the time cost with these estimates.

**Requests**:

- \$ 0.20 per 1M requests
- Scenes per day: 750
- Days per year: 365

Roughly \$0.05/year.

### DynamoDB

**Reads**:

- Scenes per day: 750
- Percentage of time when scene is below max cloud cover: 0.3
- Quadkeys per scene: ~10
- 1 read per quadkey
- Days per year: 365
- \$0.25 per million reads

Roughly \$0.21/year.

**Writes**:

- Scenes per day: 750
- Percentage of time when scene is below max cloud cover: 0.3
- Quadkeys per scene: ~10
- 1 write per quadkey
- Days per year: 365
- \$1.25 per million reads

Roughly \$1.02/year.
