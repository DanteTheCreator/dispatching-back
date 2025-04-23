from selenium_agency.api.api_client import APIClient


class PeliasHandler(APIClient):

    def __init__(self):
        super().__init__(url = "https://saving-louse-apparently.ngrok-free.app?text=")
        self.base_headers = []
        

 
class GraphhopperHandler(APIClient):

    def __init__(self):
        super().__init__(url = "https://saving-louse-apparently.ngrok-free.app/")
        self.base_headers = []

    
class BulkRequestHandler(APIClient):

    def __init__(self):
        super().__init__(url=" https://saving-louse-apparently.ngrok-free.app")
        self.base_headers = []
        

# response = PeliasHandler().get(url="/v1/search", params={"text": "Lady st 29201 columbia"})
# print(response)