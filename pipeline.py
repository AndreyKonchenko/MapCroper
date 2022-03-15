import argparse
import os
import logging
import sys
import pipeline_utils as utils


class parseLatLonArg(argparse.Action):
    def __call__(self, parser, args, values, option_string=None):
        lonlat = values.split(',')
        setattr(args, self.dest, [float(lonlat[0][1:]), float(lonlat[1][:-1])])


def main():

    parser = argparse.ArgumentParser(
        description='MapCrop 1.0 data pipeline',
        usage='python pipeline.py --plan_id 5c8ea7821cf131376f7a8743 --dst_folder data/out/sample --location "(-99.55057,28.7803)"')

    parser.add_argument('--plan_id', dest='plan_id', action='store', required=True,
                        help='The DroneDeploy plan_id.')

    parser.add_argument('--resolution', dest='resolution', action='store',
                        default=5,
                        help='The DroneDeploy map resolution in cm/pixel. Defaults to 5cm/pixel. Lower numbers give slower exports and bigger files.')

    parser.add_argument('--api_key', dest='api_key', action='store', 
                        help='API key for DroneDeploy API.')

    parser.add_argument('--dst_folder', dest='dst_folder', action='store', required=True,
                        help='The destination folder. Will be automatically created.')

    parser.add_argument('--sizex', dest='sizex', action='store',  default=100,
                        help='size at x')
    parser.add_argument('--sizey', dest='sizey', action='store',  default=100,
                        help='size at y')
    parser.add_argument('--location', dest='lonlat', action=parseLatLonArg, required=True,
                        help='The location of the wellsite (no whitespace), e.g --location (-130.2,32.1)')

    parser.add_argument('--log_level', dest='log_level', action=parseLatLonArg,
                        default='INFO',
                        help='DEBUG|INFO|WARNING|ERROR')

    args = parser.parse_args()

    logging.basicConfig(stream=sys.stdout,
                        level=logging.getLevelName(args.log_level),
                        format='%(asctime)s [%(levelname)s]: %(message)s')
    logger = logging.getLogger(__name__)

    args.dst_folder = utils.ensure_unique_folder(args.dst_folder)
    os.makedirs(args.dst_folder)

    boundary_file = os.path.join(args.dst_folder, 'boundary.json')
    bounded_gtiff = os.path.join(args.dst_folder, 'bounded.tif')
    clipped_gtiff = os.path.join(args.dst_folder, 'clipped.tif')

    sizex=args.sizex
    sizey=args.sizey

    logger.info('Getting data from DroneDeploy...')
    geotiff = utils.get_geotiff_from_dronedeploy(
        api_key=args.api_key,
        plan_id=args.plan_id,
        resolution=args.resolution,
        dst_folder=args.dst_folder)

    logger.info('Calculating boundaries for clipping...')
    box = utils.box(args.lonlat, (sizex, sizey))
    utils.write_geojson(dst_filename=boundary_file, features=box)

    logger.info('Creating new GeoTIFF matching boundaries of clipping...')
    utils.bound(src_filename=geotiff, boundary_file=boundary_file, dst_filename=bounded_gtiff)

    logger.info('Clipping...')
    utils.clip(src_filename=bounded_gtiff, boundary_file=boundary_file, dst_filename=clipped_gtiff)

    logger.info('Results saved in {}'.format(args.dst_folder))


if __name__ == '__main__':
    main()
