"""
landsat_mosaic_latest.quadkey_index.py: Create path-row to quadkey index
"""
from typing import List

import mercantile
from shapely.geometry import Polygon, asShape
from shapely.prepared import prep


def create_index(path, quadkey_zoom):
    """Create index of path-row to quadkey_zoom
    """
    # Dynamic import so that geopandas doesn't need to be global dependency
    import geopandas as gpd

    # Load shapefile
    gdf = gpd.read_file(path)

    # Iterate over rows
    data = {}
    for row in gdf.itertuples():
        # 6-character string, with a three-character left-padded PATH and then a
        # three-character left-padded ROW
        # E.g. 013001 for path 13 and row 1
        pathrow = row.PR

        quadkeys = list(find_quadkeys(row.geometry, quadkey_zoom))

        data[pathrow] = quadkeys

    return data


def find_quadkeys(geom: Polygon, quadkey_zoom: int) -> List[str]:
    """Find quadkeys of mercator tiles that intersect geometry

    First, find all tiles that overlap with the geometry's bounding box, then
    intersect each of the mercator tiles with the geometry to be sure that they
    actually intersect.
    """
    tiles = mercantile.tiles(*geom.envelope.bounds, quadkey_zoom)
    prepared_geom = prep(geom)

    intersecting_tiles = []
    for tile in tiles:
        tile_geom = asShape(mercantile.feature(tile)['geometry'])
        if prepared_geom.intersects(tile_geom):
            intersecting_tiles.append(tile)

    return (mercantile.quadkey(t) for t in intersecting_tiles)
