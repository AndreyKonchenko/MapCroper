import os

import pipeline_utils
from dronedeploy import DroneDeploy
from pprint import pprint
import time




def main():
    client = DroneDeploy(api_key='f981a5432a6c4e5bb6f1b276a5c19b90')

    #p = client.get_projects()

    #client.get_exports(project_id='')
    #pprint(p)


    plan_id = "5c8ea7821cf131376f7a8743"
    resolution = 8
    #
    # print(client.get_export(plan_id=plan_id, resolution=resolution))
    #
    export = client.find_export(plan_id=plan_id, resolution=resolution, status=['PROCESSING', 'QUEUED'])
    if export:
        print('Export job with identical parameters already in progress, using that one')
        export_id = export['id']
    else:
        print("Export job started. ", end='')
        export_id = client.create_export(plan_id=plan_id, resolution=resolution)

    done = False
    i = 0
    while not done:

        export = client.get_export(export_id=export_id)
        if export['status'] == 'COMPLETE':
            print('done!')
            break

        print("Export job {}{}         \r".format(export['status'], '.' * i), end='')

        i += 1
        time.sleep(5)


    out = 'data/out/dronedeploy'
    out = pipeline_utils.ensure_unique_folder(out)
    os.makedirs(out)

    zip_filename = os.path.join(out, 'dronedeploy.zip')
    client.download_export(export_id, zip_filename)

    print('Unzipping...')
    pipeline_utils.extract_zip(zip_filename, out)

    # exports = client.get_exports(plan_id="5c8ea7821cf131376f7a8743", limit=5)
    # pprint(exports)

    # os.makedirs('data/out/drone')
    #
    #
    #
    # print('Downloading...')
    # client.download_export('5ca623b572d6f30001816048', 'data/out/drone/mytiff.zip')
    # print('Unzipping...')
    # pipeline_utils.extract_zip('data/out/drone/mytiff.zip', 'data/out/drone')
    # print('done')

    #r = client.get_plans()
    #pprint(r)


if __name__ == '__main__':
    main()
