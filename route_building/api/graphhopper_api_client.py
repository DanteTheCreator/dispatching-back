
from ...api_client import APIClient

class GraphhopperApiClient(APIClient):

    def __init__(self, root_url):
        super().__init__(url = f"{root_url}/")
        self.base_headers = {
            "x-api-key": "dispatchingisprofitableapikey",
        }