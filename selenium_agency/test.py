import requests

def make_request(token):
    # Define the headers

    headers = {
    'accept': 'application/json',
    'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
    'authorization': f'Bearer {token}',
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
    'limit': 250,
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

    response = requests.post('https://bff.centraldispatch.com/listing-search/api/open-search', headers=headers, json=json_data)
    return response
