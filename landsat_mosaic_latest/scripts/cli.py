import json
import zlib

import click
from landsat_mosaic_latest.pathrow_index import create_index


@click.group()
def main():
    pass


@click.command()
@click.option(
    '-z',
    '--quadkey-zoom',
    type=int,
    help='Quadkey zoom level to use in index. 7 or 8 is a good choice.',
    required=True)
@click.option('--gzip/--no-gzip', default=False, help='Apply gzip compression')
@click.option(
    '--jsonl/--no-jsonl',
    default=False,
    help='Return newline-delimited JSON instead of regular JSON')
@click.argument('grid-path', type=click.Path(exists=True, readable=True))
def pathrow_index(quadkey_zoom, grid_path, gzip, jsonl):
    """Create file of path-rows to quadkeys

    Data is returned to stdout as JSON or newline-delimited JSON, where the key
    is the path-row as a string, and the value is a list of strings of quadkeys.
    The path-row string is six characters: the first three correspond to a
    left-padded path, and the second three correspond to a left-padded row. So a
    path of 13 and a row of 1 would be stored in a string as '013001'.
    """
    index = create_index(path=grid_path, quadkey_zoom=quadkey_zoom)

    # Create body as string
    if jsonl:
        lines = [
            json.dumps({k: v}, separators=(',', ':')) for k, v in index.items()]
        text = '\n'.join(lines)
    else:
        text = json.dumps(index, separators=(',', ':'))

    if gzip:
        body = _compress_gz(text)
    else:
        body = text.encode('utf-8')

    click.echo(body)


def _compress_gz(data: str) -> bytes:
    gzip_compress = zlib.compressobj(9, zlib.DEFLATED, zlib.MAX_WBITS | 16)

    return (
        gzip_compress.compress(data.encode("utf-8")) + gzip_compress.flush())


main.add_command(pathrow_index)

if __name__ == '__main__':
    main()
