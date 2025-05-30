import sys
import os
# Add the parent directory to the Python path to find the resources module
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from api_client import APIClient

class PeliasApiClient(APIClient):

    lado_pc = "https://silhouette.ge/api"
    vms_pc = "http://178.134.149.165:3333/api"
    root_url = vms_pc

    def __init__(self):
        super().__init__(url = f"{self.root_url}?text=")
        self.base_headers = {
            "x-api-key": "dispatchingisprofitableapikey",
        }
        