import json
import os
import time
import zipfile
from math import sqrt, atan, pi
import logging
import requests

import math
import geojson
import pyproj
import rasterio
import rasterio.mask
import rasterio.shutil
import rasterio.merge
from rasterio.warp import calculate_default_transform, reproject, Resampling
from shapely.geometry import Polygon

from dronedeploy import DroneDeploy


def ensure_unique_folder(folder_name: str) -> str:
    """ Automatically generates a unique folder name by adding an incrementing number. """
    full_path = os.path.abspath(folder_name)

    if not os.path.exists(full_path):
        return full_path

    basename = os.path.basename(full_path)
    _, ext = os.path.splitext(basename)

    parent = os.path.dirname(full_path)
    index = 0
    siblings = set(os.listdir(parent))
    candidate = basename + ext
    while candidate in siblings:
        candidate = "{}_{}{}".format(basename, index, ext)
        index += 1
    return os.path.join(parent, candidate)


def write_geojson(dst_filename: str, features):
    # feature is a shapely geometry type
    geom_in_geojson = geojson.Feature(geometry=features, properties={})
    with open(dst_filename, 'w') as f:
        geojson.dump(geom_in_geojson, f)


def box(lonlat: (float, float), size: (float, float)) -> Polygon:
    """
    To calculate the four corner points of a square where the provided point is the center.

    latitude and longitue in WGS84
    size[0] and size[1] in meters
    """

    wgs84 = pyproj.Geod(ellps='WGS84')

    # Rectangle Diagonal
    rect_diag = sqrt(size[0] ** 2 + size[1] ** 2)

    azimuth1 = atan(size[0] / size[1])
    azimuth2 = atan(-size[0] / size[1])
    azimuth3 = atan(size[0] / size[1]) + pi  # first point + 180 degrees
    azimuth4 = atan(-size[0] / size[1]) + pi  # second point + 180 degrees

    pt1_lon, pt1_lat, _ = wgs84.fwd(
        lonlat[0], lonlat[1], azimuth1 * 180 / pi, rect_diag)
    pt2_lon, pt2_lat, _ = wgs84.fwd(
        lonlat[0], lonlat[1], azimuth2 * 180 / pi, rect_diag)
    pt3_lon, pt3_lat, _ = wgs84.fwd(
        lonlat[0], lonlat[1], azimuth3 * 180 / pi, rect_diag)
    pt4_lon, pt4_lat, _ = wgs84.fwd(
        lonlat[0], lonlat[1], azimuth4 * 180 / pi, rect_diag)

    return Polygon([
        [pt1_lon, pt1_lat],
        [pt2_lon, pt2_lat],
        [pt3_lon, pt3_lat],
        [pt4_lon, pt4_lat],
        [pt1_lon, pt1_lat]])


def bound(src_filename: str, boundary_file: str, dst_filename: str, logger=None):
    """
    Makes a copy of the src file with the bounds defined by the GeoJson. This may either shrink
    or grow the boundaries (fill with nodata).

    :param src_filename:
    :param boundary_file:
    :param dst_filename:
    :param logger:
    :return:
    """

    logger = logger or logging.getLogger(__name__)

    with open(boundary_file, "r") as f:
        boundary = json.load(f)

    bounds = rasterio.features.bounds(boundary)

    with rasterio.open(src_filename) as src:

        dest, transform = rasterio.merge.merge([src], bounds=bounds)

        profile = src.profile
        profile['transform'] = transform
        profile['height'] = dest.shape[1]
        profile['width'] = dest.shape[2]
        profile['driver'] = 'GTiff'
        profile['count'] = dest.shape[0]

        with rasterio.open(dst_filename, 'w', **profile) as dst:
            dst.write(dest)

            for c in range(1, src.count + 1):
                try:
                    colormap = src.colormap(c)
                    dst.write_colormap(1, colormap)
                except ValueError:
                    logger.debug('No colormap for band, skipping.')


def clip(src_filename: str, boundary_file: str, dst_filename: str, logger=None):
    """
    Clips the src image to the features of the geojson file
    :param src_filename:
    :param boundary_file:
    :param dst_filename:
    :param logger:
    :return:
    """

    logger = logger or logging.getLogger(__name__)

    with open(boundary_file, "r") as f:
        boundary = json.load(f)
        features = [boundary['geometry']]

    with rasterio.open(src_filename) as src:
        out_image, out_transform = rasterio.mask.mask(
            src, features, crop=False, nodata=0)
        out_meta = src.meta.copy()

        out_meta.update({"driver": "GTiff",
                         "height": out_image.shape[1],
                         "width": out_image.shape[2],
                         "transform": out_transform})

        with rasterio.open(dst_filename, "w", **out_meta) as dst:
            dst.write(out_image)

            for c in range(1, src.count + 1):
                try:
                    colormap = src.colormap(c)
                    dst.write_colormap(1, colormap)
                except ValueError:
                    logger.debug('No colormap for band, skipping.')

def get_geotiff_from_dronedeploy(api_key: str, plan_id: str, resolution: int, dst_folder: str, logger=None) -> str:
    logger = logger or logging.getLogger(__name__)
    client = DroneDeploy(api_key=api_key)

    export = client.find_export(
        plan_id=plan_id,
        resolution=resolution,
        status=['PROCESSING', 'QUEUED'])

    if export:
        logger.info(
            'Export job with identical parameters already in progress, using that one')
        export_id = export['id']
    else:
        logger.info("Export job started. ")
        export_id = client.create_export(
            plan_id=plan_id, resolution=resolution)

    done = False
    i = 0
    while not done:

        export = client.get_export(export_id=export_id)
        if export['status'] == 'COMPLETE':
            break

        logger.info("Export job {}, waiting 5s...{}\r".format(
            export['status'], '.' * i))

        i += 1
        time.sleep(5)

    zip_filename = os.path.join(dst_folder, 'dronedeploy.zip')
    client.download_export(export_id, zip_filename)

    logger.info('Unzipping...')
    with zipfile.ZipFile(zip_filename, 'r') as zip_ref:

        geotiff = None
        for f in zip_ref.filelist:
            if f.filename.lower().endswith('.tif'):
                geotiff = f.filename
                break

        zip_ref.extract(geotiff, dst_folder)

    return os.path.join(dst_folder, geotiff)


def download_url(url, filename, logger=None):

    logger = logger or logging.getLogger(__name__)

    progress_bar = '.........................................'
    block_size = 512 * 1024

    r = requests.get(url, stream=True)
    file_size = int(r.headers['Content-Length'])
    with open(filename, 'wb') as f:
        i = 0
        for chunk in r.iter_content(block_size):
            f.write(chunk)
            i += block_size
            status = int((i * len(progress_bar)) / file_size)
            logger.info('Downloading [{}{}]\r'.format(
                progress_bar[:status],
                ' ' * (len(progress_bar) - status)
            ))
