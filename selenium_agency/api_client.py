import requests
import json

class APIClient:
    def __init__(self, url, origin=None):
        self.url = url
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
 
    def get(self, url, token=None, params=None):
        headers = self._get_headers(token)
        response = requests.get(url, params=params, headers=headers)
        return response

    def post(self, url, token=None, payload=None, params=None):
        headers = self._get_headers(token)
        response = requests.post(url, headers=headers, json=payload, params=params)
        return response
