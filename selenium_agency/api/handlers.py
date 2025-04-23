from selenium_agency.api.api_client import APIClient


class PeliasHandler(APIClient):

    def __init__(self):
        super().__init__(url = "http://176.221.230.243/api?text=")
        self.base_headers = {
            "x-api-key": "dispatchingisprofitableapikey",
        }
        

 
class GraphhopperHandler(APIClient):

    def __init__(self):
        super().__init__(url = "http://176.221.230.243/api/")
        self.base_headers = {
            "x-api-key": "dispatchingisprofitableapikey",
        }

    
class BulkRequestHandler(APIClient):

    def __init__(self):
        super().__init__(url="http://176.221.230.243/api")
        self.base_headers = {
            "x-api-key": "dispatchingisprofitableapikey",
        }
        

# response = PeliasHandler().get(url="/v1/search", params={"text": "Lady st 29201 columbia"})
# print(response)