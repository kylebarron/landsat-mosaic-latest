# landsat-mosaic-latest

Auto-updating Landsat 8 mosaics from AWS SNS notifications.

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
an AWS Lambda function to run when those notifications are sent, and update two
DynamoDB databases with identifiers for the most recent imagery per mercator
tile.

This library does not provide on-the-fly image tiling. For that, look at
[`awspds-mosaic`](https://github.com/kylebarron/awspds-mosaic).

Also note that this library creates a new DynamoDB table but does not populate
it with initial values: it only updates the table as new imagery comes in. See
instructions below to create an initial Landsat mosaic.

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
order to keep things simple, eliminate geospatial dependencies, and create
efficient an MosaicJSON, this package relies on a prebuilt index that associates
those path-row combinations to the mercator tile quadkeys used by the tiler.

By default, this library ships with a worldwide index at quadkey zoom level 8.
If you need a differing quadkey zoom or want to restrict your mosaic to a
geographic bounding box, you can build your own index.

The script to create an index is stored in
[`landsat-cogeo-mosaic`][landsat-cogeo-mosaic]. For full instructions, see its
[project docs][index_cli].

[index_cli]: https://kylebarron.dev/landsat-cogeo-mosaic/cli/#index

The standard index bundled by default with `landsat-mosaic-latest` is created
with:

```bash
landsat-cogeo-mosaic index \
    `# Path to Shapefile of path-row geometries` \
    --wrs-path data/WRS2_descending_0/WRS2_descending.shp \
    `# Path to CSV of scene metadata downloaded from AWS S3` \
    --scene-path data/scene_list.gz \
    `# Worldwide bounds` \
    --bounds '-180,-90,180,90' \
    `# Quadkey zoom` \
    --quadkey-zoom 8 \
    | gzip \
    > landsat_mosaic_latest/data/index.json.gz
```

Note it's currently imperative to write the index to that exact location in
order to be properly found during runtime.

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

By default deployment creates _two_ DynamoDB tables, one for the absolute latest
imagery, another for the latest _low-cloud_ imagery.

Then it's simple to deploy this stack with a single line:

```bash
sls deploy \
    --table-name landsat-mosaic-latest \
    --cloudless-table-name landsat-mosaic-latest-cloudless \
    --max-cloud-cover 5
```

- `table-name` is the name given to the DynamoDB table without a cloud cover filter. You'll need to provide this information to the tiler when serving imagery. Default: `landsat-mosaic-latest-cloudless`.
- `cloudless-table-name` is the name given to the DynamoDB table that uses the cloud cover filter below. Default `landsat-mosaic-latest`.
- `max-cloud-cover` is an integer between 0 and 100 that defines the maximum percent cloud cover permitted for new imagery into the cloudless DynamoDB table. If a new Landsat scene has cloud cover greater than the given percent, it will only be added to the non-cloudless DynamoDB table. Default `5`.

## Upload a base MosaicJSON

This library creates a new DynamoDB table but does not populate it with initial
values: it only updates the table as new imagery comes in. To create an inital
Landsat mosaic, we'll use [`landsat-cogeo-mosaic`][landsat-cogeo-mosaic].

Note that when creating an initial MosaicJSON, you should use the same path-row
index as in the serverless function. The below commands point to the default,
bundled `index.json.gz`.

[landsat-cogeo-mosaic]: https://github.com/kylebarron/landsat-cogeo-mosaic

### Setup

Install `cogeo-mosaic` and `landsat-cogeo-mosaic`:

```
pip install "cogeo-mosaic>=3.0a3" landsat-cogeo-mosaic
```

#### Create SQLite database of Landsat 8 metadata

For up-to-date instructions, see [`landsat-cogeo-mosaic` docs][landsat-cogeo-mosaic-docs]. But it's roughly:

[landsat-cogeo-mosaic-docs]: https://kylebarron.dev/landsat-cogeo-mosaic/examples/global/

```
git clone https://github.com/kylebarron/landsat-cogeo-mosaic/
cd landsat-cogeo-mosaic
mkdir -p data/
aws s3 cp s3://landsat-pds/c1/L8/scene_list.gz data/
gunzip -c data/scene_list.gz > data/scene_list
cd data/
sqlite3 scene_list.db < ../scripts/csv_import.sql
cd -
```

Then `scene_list.db` is the database to be used with the `--sqlite-path`
argument below.

### Latest Cloudless

Some Landsat 8 path-row combinations have _never_ had a scene with cloud cover
<5%. This command will automatically relax the `--max-cloud` restriction until
it finds a result for each path-row.

Assuming you have cloned and are in the `landsat-mosaic-latest` repository:

```bash
landsat-cogeo-mosaic create-from-db \
    `# Path to the sqlite database file` \
    --sqlite-path ../landsat-cogeo-mosaic/data/scene_list.db \
    `# Path to the path-row geometry file` \
    --pathrow-index landsat_mosaic_latest/data/index.json.gz \
    `# Min zoom of mosaic, 7 is a good default for Landsat` \
    --min-zoom 7 \
    `# Max zoom of mosaic, 12 is a good default for Landsat` \
    --max-zoom 12 \
    `# Maximum cloud cover. This means 5%` \
    --max-cloud 5 \
    `# Preference for choosing the asset for a tile` \
    --sort-preference newest \
    > mosaic_cloudless_latest.json
```

### Latest

This is almost the same as the latest cloudless command, except that it removes
the `--max-cloud` argument.

Assuming you have cloned and are in the `landsat-mosaic-latest` repository:

```bash
landsat-cogeo-mosaic create-from-db \
    `# Path to the sqlite database file` \
    --sqlite-path ../landsat-cogeo-mosaic/data/scene_list.db \
    `# Path to the path-row geometry file` \
    --pathrow-index landsat_mosaic_latest/data/index.json.gz \
    `# Min zoom of mosaic, 7 is a good default for Landsat` \
    --min-zoom 7 \
    `# Max zoom of mosaic, 12 is a good default for Landsat` \
    --max-zoom 12 \
    `# Preference for choosing the asset for a tile` \
    --sort-preference newest \
    > mosaic_latest.json
```

### Upload to DynamoDB

Then upload these two generated MosaicJSON files to DynamoDB. The `--url`
argument must match the names given to the DynamoDB tables in the `sls deploy`
step.

**Note: This will overwrite any existing data in the DynamoDB table**.

```bash
cogeo-mosaic upload \
    --url 'dynamodb://us-west-2/landsat-mosaic-latest' \
    mosaic_latest.json
cogeo-mosaic upload \
    --url 'dynamodb://us-west-2/landsat-mosaic-latest-cloudless' \
    mosaic_cloudless_latest.json
```

## Pricing

**\$2.64 per year** is a rough estimate of the cost to keep each DynamoDB table updated.

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
