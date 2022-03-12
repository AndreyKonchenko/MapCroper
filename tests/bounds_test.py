from pipeline_utils import bound
import json
import rasterio.features

with open('/Users/tvik/dev/repos/fractetris/data/out/sample_15/boundary.json', "r") as f:
    boundary = json.load(f)
    features = [boundary['geometry']]

bounds = rasterio.features.bounds(boundary)
print(bounds)


bound(
    src_filename='/Users/tvik/dev/repos/fractetris/data/out/sample_15/MapPlan_Orthomosaic_export_ThuApr11140759.861659.tif',
    dst_filename='/Users/tvik/dev/repos/fractetris/data/out/sample_15/bounded.tif',
    bounds=bounds)
