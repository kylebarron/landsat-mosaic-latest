"""
landsat_mosaic_latest.landsat: Utilities for landsat scene and metadata parsing

This code is copied from rio-tiler and rio-toa. Since I only need metadata
parsing, I can avoid dependencies on numpy, GDAL completely by just copying this
parsing.

rio-toa is licensed BSD
https://github.com/mapbox/rio-toa/blob/e94c75b6ca720eefbb88cc777cb69f6608485d3e/setup.py#L30

rio-tiler is licensed BSD-3
https://github.com/cogeotiff/rio-tiler/blob/master/LICENSE.txt
"""

import datetime
import os
import re
from typing import Any, Dict
from urllib.request import urlopen


class RioTilerError(Exception):
    """Base exception class."""


class InvalidLandsatSceneId(RioTilerError):
    """Invalid Landsat-8 scene id."""


def landsat_parser(sceneid: str) -> Dict:
    """
    Parse Landsat-8 scene id.
    Author @perrygeo - http://www.perrygeo.com
    Attributes
    ----------
        sceneid : str
            Landsat sceneid.
    Returns
    -------
        out : dict
            dictionary with metadata constructed from the sceneid.
    """
    pre_collection = r"(L[COTEM]8\d{6}\d{7}[A-Z]{3}\d{2})"
    collection_1 = r"(L[COTEM]08_L\d{1}[A-Z]{2}_\d{6}_\d{8}_\d{8}_\d{2}_(T1|T2|RT))"
    if not re.match("^{}|{}$".format(pre_collection, collection_1), sceneid):
        raise InvalidLandsatSceneId("Could not match {}".format(sceneid))

    precollection_pattern = (
        r"^L"
        r"(?P<sensor>\w{1})"
        r"(?P<satellite>\w{1})"
        r"(?P<path>[0-9]{3})"
        r"(?P<row>[0-9]{3})"
        r"(?P<acquisitionYear>[0-9]{4})"
        r"(?P<acquisitionJulianDay>[0-9]{3})"
        r"(?P<groundStationIdentifier>\w{3})"
        r"(?P<archiveVersion>[0-9]{2})$")

    collection_pattern = (
        r"^L"
        r"(?P<sensor>\w{1})"
        r"(?P<satellite>\w{2})"
        r"_"
        r"(?P<processingCorrectionLevel>\w{4})"
        r"_"
        r"(?P<path>[0-9]{3})"
        r"(?P<row>[0-9]{3})"
        r"_"
        r"(?P<acquisitionYear>[0-9]{4})"
        r"(?P<acquisitionMonth>[0-9]{2})"
        r"(?P<acquisitionDay>[0-9]{2})"
        r"_"
        r"(?P<processingYear>[0-9]{4})"
        r"(?P<processingMonth>[0-9]{2})"
        r"(?P<processingDay>[0-9]{2})"
        r"_"
        r"(?P<collectionNumber>\w{2})"
        r"_"
        r"(?P<collectionCategory>\w{2})$")

    for pattern in [collection_pattern, precollection_pattern]:
        match = re.match(pattern, sceneid, re.IGNORECASE)
        if match:
            meta: Dict[str, Any] = match.groupdict()
            break

    meta["scene"] = sceneid
    if meta.get("acquisitionJulianDay"):
        date = datetime.datetime(
            int(meta["acquisitionYear"]), 1,
            1) + datetime.timedelta(int(meta["acquisitionJulianDay"]) - 1)

        meta["date"] = date.strftime("%Y-%m-%d")
    else:
        meta["date"] = "{}-{}-{}".format(
            meta["acquisitionYear"], meta["acquisitionMonth"],
            meta["acquisitionDay"])

    collection = meta.get("collectionNumber", "")
    if collection != "":
        collection = "c{}".format(int(collection))

    meta["scheme"] = "s3"
    meta["bucket"] = "landsat-pds"
    meta["prefix"] = os.path.join(
        collection, "L8", meta["path"], meta["row"], sceneid)

    return meta


def _landsat_get_mtl(sceneid: str) -> Dict:
    """
    Get Landsat-8 MTL metadata.
    Attributes
    ----------
        sceneid : str
            Landsat sceneid. For scenes after May 2017,
            sceneid have to be LANDSAT_PRODUCT_ID.
    Returns
    -------
        out : dict
            returns a JSON like object with the metadata.
    """
    scene_params = landsat_parser(sceneid)
    meta_file = "http://{bucket}.s3.amazonaws.com/{prefix}/{scene}_MTL.txt".format(
        **scene_params)
    metadata = str(urlopen(meta_file).read().decode())
    return _parse_mtl_txt(metadata)


def _parse_mtl_txt(mtltxt):
    group = re.findall('.*\n', mtltxt)

    is_group = re.compile(r'GROUP\s\=\s.*')
    is_end = re.compile(r'END_GROUP\s\=\s.*')
    get_group = re.compile('\=\s([A-Z0-9\_]+)')

    output = [{'key': 'all', 'data': {}}]

    for g in map(str.lstrip, group):
        if is_group.match(g):
            output.append({'key': get_group.findall(g)[0], 'data': {}})

        elif is_end.match(g):
            endk = output.pop()
            k = u'{}'.format(endk['key'])
            output[-1]['data'][k] = endk['data']

        else:
            k, d = _parse_data(g)
            if k:
                k = u'{}'.format(k)
                output[-1]['data'][k] = d

    return output[0]['data']


def _cast_to_best_type(kd):
    key, data = kd[0]
    try:
        return key, int(data)
    except ValueError:
        try:
            return key, float(data)
        except ValueError:
            return key, u'{}'.format(data.strip('"'))


def _parse_data(line):
    kd = re.findall(r'(.*)\s\=\s(.*)', line)

    if len(kd) == 0:
        return False, False
    else:
        return _cast_to_best_type(kd)
