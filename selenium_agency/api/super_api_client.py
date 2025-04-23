from selenium_agency.api.api_client import APIClient

class SuperAPIClient(APIClient):
    def __init__(self):
        super().__init__(url="https://api.loadboard.superdispatch.com",)
        origin = "https://carrier.superdispatch.com"
        self.base_headers = {
            'accept': 'application/json',
            'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'content-type': 'application/json',
            'origin': 'https://carrier.superdispatch.com',
            'priority': 'u=1, i',
            "referer": origin + "/" if origin else None,
            'sec-ch-ua': '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
        }

    def set_authorization_header(self, token):
        self.base_headers['authorization'] = f"Token {token}"