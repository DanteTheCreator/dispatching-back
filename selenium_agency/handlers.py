from api_client import APIClient


class PeliasHandler(APIClient):

    def __init__(self):
        super().__init__(url = "https://f735-176-221-230-243.ngrok-free.app", origin="")
        self.base_headers = []
        

 
class GraphhopperHandler(APIClient):

    def __init__(self):
        super().__init__(url = "https://b049-176-221-230-243.ngrok-free.app", origin="")
        self.base_headers = []

    
class BulkRequestHandler(APIClient):

    def __init__(self):
        super().__init__(url="http://f735-176-221-230-243.ngrok-free.app/")
        self.base_headers = []
        

# response = PeliasHandler().get(url="/v1/search", params={"text": "Lady st 29201 columbia"})
# print(response)