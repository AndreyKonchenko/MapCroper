import requests
import logging
import pipeline_utils


class DroneDeploy:

    def __init__(self, api_key: str, logger=None):
        self._api_key = api_key
        self._headers = {"Authorization": 'Bearer {}'.format(api_key)}
        self._logger = logger or logging.getLogger(__name__)

    def _run_query(self, query):
        request = requests.post(
            'https://api.dronedeploy.com/graphql?', json={'query': query}, headers=self._headers)
        if request.status_code == 200:
            return request.json()
        else:
            raise Exception("Query failed to run by returning code of {}. {}".format(
                request.status_code, query))

    def get_projects(self) -> [(str, str)]:
        query = """
            {
            projects {
              edges {
                node {
                  id
                    name
                }
              }
            }  
        }"""

        result = self._run_query(query)
        projects = []
        for node in result['data']['projects']['edges']:
            node = node['node']
            projects.append(
                {
                    'id': node['id'].replace('Project:', ''),
                    'name': node['name']
                }
            )
        return projects

    def get_exports(self, plan_id, limit):

        if not plan_id.startswith('Export:'):
            plan_id = 'MapPlan:' + plan_id

        query_template = """
            query GetExports{
              node(id:"%s"){
                ... on MapPlan{
                  exports(first:%s){
                    edges {
                      node {
                        id
                        status
                        parameters {
                          resolution,
                          fileFormat,
                          layer
                        }
                        downloadPath
                      }
                    }
                  }
                }
              }
            }
        """

        query = query_template % (plan_id, limit)

        result = self._run_query(query)
        exports = []
        for edge in result['data']['node']['exports']['edges']:
            exports.append(edge['node'])

        return exports

    def create_export(self, plan_id, resolution) -> str:
        query_template = """
        mutation {
            createExport(input: {planId: "MapPlan:%s", parameters: {layer: ORTHOMOSAIC, resolution:%s, projection:4326}}) {
                export {
                    id
                }
            }
        }"""

        query = query_template % (plan_id, resolution)
        result = self._run_query(query)
        return result['data']['createExport']['export']['id']

    def get_export(self, export_id):

        if not export_id.startswith('Export:'):
            export_id = 'Exports:' + export_id

        query_template = """
            query {
                export(id:"%s") {
                    id
                    status
                    parameters {
                        projection
                        merge
                        contourInterval
                        layer
                        fileFormat
                        resolution
                    }
                    downloadPath
                }
            }
        """

        query = query_template % export_id
        result = self._run_query(query)
        return result['data']['export']

    def find_export(self, plan_id: str, resolution: int, status: [str]) -> bool:

        exports = self.get_exports(plan_id=plan_id, limit=100)
        for export in exports:
            if export['parameters']['resolution'] != resolution:
                continue
            if export['parameters']['layer'] != 'ORTHOMOSAIC':
                continue
            if export['parameters']['fileFormat'] != 'GEO_TIFF':
                continue
            if not export['status'] in status:
                continue

            return export

        return None

    def download_export(self, export_id, filename):

        export = self.get_export(export_id=export_id)
        if not export['status'] == 'COMPLETE':
            raise ValueError('Export not complete.')

        pipeline_utils.download_url(export['downloadPath'], filename)
