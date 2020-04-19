"""
landsat_mosaic_latest.aws: Interact with AWS services
"""

import json
from typing import Dict, List


def parse_message(body: Dict) -> List[str]:
    message = body['Message']

    # I'm not sure if message is always a JSON encoded string, or if sometimes
    # it can be a dict already
    if isinstance(message, str):
        message = json.loads(message)

    records = message['Records']
    keys = [r['s3']['object']['key'] for r in records]
    scene_ids = [key.split('/')[-2] for key in keys]
    return scene_ids
