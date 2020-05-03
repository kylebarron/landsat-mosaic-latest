import gzip
import json
import os
from pathlib import Path
from typing import List, Optional

from landsat_mosaic_latest.aws import (
    dynamodb_client, fetch_dynamodb, parse_sns_message, write_dynamodb)
from landsat_mosaic_latest.landsat import _landsat_get_mtl, landsat_parser


def main(
        sns_message,
        dynamodb_table_name: str = os.environ['DYNAMODB_TABLE_NAME'],
        max_cloud_cover: float = float(os.getenv('MAX_CLOUD_COVER', '20')),
        cloud_cover_land: bool = True):
    client = dynamodb_client()
    dynamodb_table = client.Table(dynamodb_table_name)

    # Find new scene ids from SNS message
    scene_ids = parse_sns_message(sns_message)

    # Find filesystem path to index data file
    index_path = index_data_path()

    for scene_id in scene_ids:
        scene_meta = landsat_parser(scene_id)

        # Skip unless real-time (RT) collection
        if scene_meta['collectionCategory'] != 'RT':
            continue

        # Find cloud cover
        cloud_cover = get_cloud_cover(scene_id, cloud_cover_land)
        if cloud_cover > max_cloud_cover:
            continue

        # Find overlapping quadkeys
        path = scene_meta['path']
        row = scene_meta['row']
        quadkeys = find_quadkeys(index_path, path=path, row=row)

        for quadkey in quadkeys:
            update_dynamodb_quadkey(
                dynamodb_table=dynamodb_table,
                quadkey=quadkey,
                scene_id=scene_id,
                path=path,
                row=row)


def update_dynamodb_quadkey(dynamodb_table, quadkey, scene_id, path, row):
    # Retrieve existing assets from DynamoDB
    existing = fetch_dynamodb(dynamodb_table, quadkey)

    # If an existing asset has the same path-row as this one, remove it from the
    # list
    new_scene_ids = []
    for existing_scene_id in existing.get('assets', []):
        existing_scene_meta = landsat_parser(existing_scene_id)
        existing_path = existing_scene_meta['path']
        existing_row = existing_scene_meta['row']
        if (path != existing_path) and (row != existing_row):
            new_scene_ids.append(existing_scene_id)

    # Add new scene id
    new_scene_ids.append(scene_id)

    # Write new assets to DynamoDB
    write_dynamodb(dynamodb_table, quadkey, new_scene_ids)


def find_quadkeys(index_path, path, row,
                  jsonl: Optional[bool] = None) -> List[str]:
    """Find intersecting quadkeys
    """
    pathrow = path.zfill(3) + row.zfill(3)

    # Use gzip file opener if path ends with .gz
    file_opener = gzip.open if index_path.endswith('.gz') else open
    mode = 'rt' if index_path.endswith('.gz') else 'r'

    # Set jsonl to true if `.json` is in filename
    jsonl = True if jsonl is None and '.jsonl' in index_path else jsonl

    with file_opener(index_path, mode) as f:
        if jsonl:
            for line in f:
                line_dict = json.loads(line)
                quadkeys = line_dict.get(pathrow)
                if quadkeys:
                    return quadkeys

        else:
            index = json.load(f)
            return index.get(pathrow, [])

    return []


def get_cloud_cover(scene_id: str, land: bool = True):
    """Get cloud cover value

    Args:
        - scene_id: landsat scene_id
        - land: use CLOUD_COVER_LAND instead of CLOUD_COVER
    """
    meta = _landsat_get_mtl(scene_id)
    image_attrs = meta['L1_METADATA_FILE']['IMAGE_ATTRIBUTES']
    cloud_key = 'CLOUD_COVER_LAND' if land else 'CLOUD_COVER'
    return image_attrs[cloud_key]


def index_data_path():
    lambda_root = os.getenv('LAMBDA_TASK_ROOT')
    if not lambda_root:
        return str((Path(__file__) / 'data' / 'index.jsonl.gz').resolve())

    return f'{lambda_root}/landsat_mosaic_latest/data/index.jsonl.gz'
