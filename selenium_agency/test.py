import requests
import json

url = "https://api.loadboard.superdispatch.com/internal/v3/loads/search"

headers = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "authorization": "Token e8fe5c5607a740fc8507af3f01e24b4d",
    "content-type": "application/json",
    "origin": "https://carrier.superdispatch.com",
    "priority": "u=1, i",
    "referer": "https://carrier.superdispatch.com/",
    "sec-ch-ua": "\"Chromium\";v=\"134\", \"Not:A-Brand\";v=\"24\", \"Google Chrome\";v=\"134\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"Windows\"",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
}

data = {}

response = requests.post(url, headers=headers, json=data)

print(response.status_code)
print(len(response.json()['data']))