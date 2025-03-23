import requests
import json

class APIClient:
    def __init__(self, base_url=None, origin=None):
        self.base_url = base_url
        self.base_headers = {
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9",
            "content-type": "application/json",
            "origin": origin,
            "priority": "u=1, i",
            "referer": origin + "/" if origin else None,
            "sec-ch-ua": "\"Chromium\";v=\"134\", \"Not:A-Brand\";v=\"24\", \"Google Chrome\";v=\"134\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
        }

    def _get_headers(self, token=None):
        headers = self.base_headers.copy()
        if token:
            headers["authorization"] = f"Token {token}"
        return headers

    def _get_full_url(self, url):
        return f"{self.base_url}{url}" if self.base_url else url

    def get(self, url, token=None, params=None):
        headers = self._get_headers(token)
        full_url = self._get_full_url(url)
        print("request headers ", headers)
        print("\n\n\n")
        print("full url: ", full_url)
        print("\n\n\n")
        print("params: ", params)
        print("\n\n\n")
        response = requests.get(full_url, params=params, headers=headers)
        print("response headers: ", response.headers)
        print("\n\n\n")
        print("status code: ", response.status_code)
        print("\n\n\n")
        print("response content: ", response.content)
        print("\n\n\n")
        return response

    def post(self, url, token=None, payload=None, params=None):
        headers = self._get_headers(token)
        full_url = self._get_full_url(url)
        print("headers ", headers)
        print("\n\n\n")
        print("full url: ", full_url)
        print("\n\n\n")
        print("payload: ", payload)
        print("\n\n\n")
        response = requests.post(full_url, headers=headers, json=payload, params=params)
        print("response headers: ", response.headers)
        print("\n\n\n")
        print("status code: ", response.status_code)
        print("\n\n\n")
        print("response content: ", response.content)
        print("\n\n\n")
        return response
