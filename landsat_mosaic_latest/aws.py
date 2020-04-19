"""
landsat_mosaic_latest.aws: Interact with AWS services
"""

import json
import os
from typing import Dict, List

import boto3


def parse_sns_message(body: Dict) -> List[str]:
    """Parse SNS body
    """
    message = body['Message']

    # I'm not sure if message is always a JSON encoded string, or if sometimes
    # it can be a dict already
    if isinstance(message, str):
        message = json.loads(message)

    records = message['Records']
    keys = [r['s3']['object']['key'] for r in records]
    scene_ids = [key.split('/')[-2] for key in keys]
    return scene_ids


def dynamodb_client(region: str = os.getenv('AWS_REGION', 'us-west-2')):
    return boto3.resource("dynamodb", region_name=region)


def fetch_dynamodb(table, quadkey: str) -> Dict:
    return table.get_item(Key={"quadkey": quadkey}).get("Item", {})


def write_dynamodb(table, quadkey, assets):
    item = {"quadkey": quadkey, "assets": assets}
    table.put_item(Item=item)
