from selenium_agency.api.api_client import APIClient

lado_pc = "https://silhouette.ge/api"
vms_pc = "http://178.134.149.165:3333/api"

root_url = vms_pc


class PeliasHandler(APIClient):

    def __init__(self):
        super().__init__(url = f"{root_url}?text=")
        self.base_headers = {
            "x-api-key": "dispatchingisprofitableapikey",
        }
        

 
class GraphhopperHandler(APIClient):

    def __init__(self):
        super().__init__(url = f"{root_url}/")
        self.base_headers = {
            "x-api-key": "dispatchingisprofitableapikey",
        }

    
class BulkRequestHandler(APIClient):

    def __init__(self):
        super().__init__(url=f"{root_url}")
        self.base_headers = {
            "x-api-key": "dispatchingisprofitableapikey",
        }
        

# response = PeliasHandler().get(url="/v1/search", params={"text": "Lady st 29201 columbia"})
# print(response)