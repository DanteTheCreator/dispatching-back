import requests

headers = {
    'accept': 'application/json',
    'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
    'authorization': 'Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6IjQ2M0VCNThGOEJBQ0Q5RThFQTVGNDBFRUNFMkZGNzkxIiwidHlwIjoiYXQrand0In0.eyJpc3MiOiJodHRwczovL2lkLmNlbnRyYWxkaXNwYXRjaC5jb20iLCJuYmYiOjE3NDUyMzEwNTAsImlhdCI6MTc0NTIzMTA1MCwiZXhwIjoxNzQ1MjMyODUwLCJhdWQiOlsibGlzdGluZ3Mtc2VhcmNoLWFwaSIsInVzZXJfbWFuYWdlbWVudF9iZmYiXSwic2NvcGUiOlsib3BlbmlkIiwibGlzdGluZ3Nfc2VhcmNoIiwidXNlcl9tYW5hZ2VtZW50X2JmZiJdLCJhbXIiOlsicHdkIl0sImNsaWVudF9pZCI6InNpbmdsZV9zcGFfcHJvZF9jbGllbnQiLCJzdWIiOiJkMHN4YTZhZCIsImF1dGhfdGltZSI6MTc0NTIzMTA0MiwiaWRwIjoibG9jYWwiLCJ1c2VybmFtZSI6ImQwc3hhNmFkIiwidGllckdyb3VwIjoiQ2FycmllciIsImNvbXBhbnlOYW1lIjoiREFORUxBIFRSQU5TUE9SVEFUSU9OIENPUlAiLCJjdXN0b21lcklkIjoiM2M1YjQyYWItZWMxMy00ZTAxLTliNDQtNzVlMTMwNjlhNDNkIiwiYWN0aXZhdGlvbkRhdGUiOiIyMDI1LTA0LTE0IDEzOjEzOjEwIiwiYWNjb3VudFN0YXR1cyI6IkFjdGl2ZSIsImlzQWN0aXZlIjp0cnVlLCJ1c2VySWQiOiJhNWQxYjE3Zi1mMmRjLTQzZjEtYjZkZS0zMDQ0MTRkMTkyNGQiLCJyb2xlcyI6WyJPV05FUiJdLCJtYXJrZXRQbGFjZUlkcyI6WzEwMDAwXSwibWFya2V0cGxhY2VzIjpbeyJNYXJrZXRwbGFjZUlkIjoxMDAwMCwiQWN0aXZlIjp0cnVlLCJSZWFzb25Db2RlIjoiQ29tcGxldGUvQWN0aXZhdGVkIn1dLCJudW1iZXJPZkFjY291bnRzIjoiMSIsImxvZ2luVXNlcm5hbWUiOiJEYW5lbGFUcmFuc3BvcnRhdGlvbkNvcnAiLCJmaXJzdE5hbWUiOiJCRVNBUklPTiIsImxhc3ROYW1lIjoiREFORUxJQSIsImVtYWlsIjoiZGFuZWxhdHJhbnNwb3J0YXRpb25jb3JwQGdtYWlsLmNvbSIsInByb2R1Y3RzIjpbeyJQcm9kdWN0SWQiOiI2MTcyYmVhMC1kOGFhLTRhZWEtODk2OC0wOTg1NzgxZDUyZmUiLCJNYXJrZXRwbGFjZUlkIjoxMDAwMCwiUHJvZHVjdFN0YXR1c0tleSI6ImFjdGl2ZSJ9XSwibWZhRXhwaXJhdGlvbiI6IjE3NDUyMzQ2NDIiLCJwYXJ0bmVySWQiOiIiLCJzaWQiOiI2REJDOTc4ODZDMDU5QUQyNzQ4REFBMjc4NjdBNDA5MiJ9.S6SeXmHMrJiox9cl3xdIaA3z2SWB1xDunvu7NVjc24rVG9sVY4CEBAxanFB78p_EvjMiLh9kyVBtWTcG6NuytrXo_146e8S9PC66J7C2EAjqFvizykOI1xb1xeOV89loH8_K0u3cdRM3iYeAo0uO9g8l1h96pyJhCH70e4SfE8apxaUeXuTBxdXeIQDjhxEifoP240mNUzz8_6UOn-pXI-WUfa8RgntUTqAzviHadpat1J6vhfx-eQObbdjiYdix27GW5KjTgPvUm6o0XswHgXH5IDerzONwEYbCK-s2U1SfSdE3COXnaGJtOI0WpEwl-C6bh0zk_Mc0zVlOlMo_Yg',
    'content-type': 'application/json',
    'origin': 'https://app.centraldispatch.com',
    'priority': 'u=1, i',
    'referer': 'https://app.centraldispatch.com/',
    'sec-ch-ua': '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-site',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
}

json_data = {
    'vehicleCount': {
        'min': 1,
        'max': None,
    },
    'postedWithinHours': None,
    'tagListingsPostedWithin': 2,
    'trailerTypes': [],
    'paymentTypes': [],
    'vehicleTypes': [],
    'operability': 'All',
    'minimumPaymentTotal': None,
    'readyToShipWithinDays': None,
    'minimumPricePerMile': None,
    'offset': 0,
    'limit': 10000,
    'sortFields': [
        {
            'name': 'PICKUP',
            'direction': 'ASC',
        },
        {
            'name': 'DELIVERYMETROAREA',
            'direction': 'ASC',
        },
    ],
    'shipperIds': [],
    'desiredDeliveryDate': None,
    'displayBlockedShippers': False,
    'showPreferredShippersOnly': False,
    'showTaggedOnTop': False,
    'marketplaceIds': [],
    'averageRating': 'All',
    'requestType': 'Open',
    'locations': [],
}

response = requests.post('https://bff.centraldispatch.com/listing-search/api/open-search', headers=headers, json=json_data).json()
print(response)
print(len(response))
