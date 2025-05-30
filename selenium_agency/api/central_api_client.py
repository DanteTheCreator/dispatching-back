from api_client import APIClient

class CentralAPIClient(APIClient):
    def __init__(self):
        super().__init__(url="",)
        origin = "https://app.centraldispatch.com"
        self.base_headers = {
            'accept': 'application/json',
            'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'authorization': 'Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6IjQ2M0VCNThGOEJBQ0Q5RThFQTVGNDBFRUNFMkZGNzkxIiwidHlwIjoiYXQrand0In0.eyJpc3MiOiJodHRwczovL2lkLmNlbnRyYWxkaXNwYXRjaC5jb20iLCJuYmYiOjE3NDUyNDcyMzksImlhdCI6MTc0NTI0NzIzOSwiZXhwIjoxNzQ1MjQ5MDM5LCJhdWQiOlsibGlzdGluZ3Mtc2VhcmNoLWFwaSIsInVzZXJfbWFuYWdlbWVudF9iZmYiXSwic2NvcGUiOlsib3BlbmlkIiwibGlzdGluZ3Nfc2VhcmNoIiwidXNlcl9tYW5hZ2VtZW50X2JmZiJdLCJhbXIiOlsicHdkIl0sImNsaWVudF9pZCI6InNpbmdsZV9zcGFfcHJvZF9jbGllbnQiLCJzdWIiOiJkMHN4YTZhZCIsImF1dGhfdGltZSI6MTc0NTIzMTA0MiwiaWRwIjoibG9jYWwiLCJ1c2VybmFtZSI6ImQwc3hhNmFkIiwidGllckdyb3VwIjoiQ2FycmllciIsImNvbXBhbnlOYW1lIjoiREFORUxBIFRSQU5TUE9SVEFUSU9OIENPUlAiLCJjdXN0b21lcklkIjoiM2M1YjQyYWItZWMxMy00ZTAxLTliNDQtNzVlMTMwNjlhNDNkIiwiYWN0aXZhdGlvbkRhdGUiOiIyMDI1LTA0LTE0IDEzOjEzOjEwIiwiYWNjb3VudFN0YXR1cyI6IkFjdGl2ZSIsImlzQWN0aXZlIjp0cnVlLCJ1c2VySWQiOiJhNWQxYjE3Zi1mMmRjLTQzZjEtYjZkZS0zMDQ0MTRkMTkyNGQiLCJyb2xlcyI6WyJPV05FUiJdLCJtYXJrZXRQbGFjZUlkcyI6WzEwMDAwXSwibWFya2V0cGxhY2VzIjpbeyJNYXJrZXRwbGFjZUlkIjoxMDAwMCwiQWN0aXZlIjp0cnVlLCJSZWFzb25Db2RlIjoiQ29tcGxldGUvQWN0aXZhdGVkIn1dLCJudW1iZXJPZkFjY291bnRzIjoiMSIsImxvZ2luVXNlcm5hbWUiOiJEYW5lbGFUcmFuc3BvcnRhdGlvbkNvcnAiLCJmaXJzdE5hbWUiOiJCRVNBUklPTiIsImxhc3ROYW1lIjoiREFORUxJQSIsImVtYWlsIjoiZGFuZWxhdHJhbnNwb3J0YXRpb25jb3JwQGdtYWlsLmNvbSIsInByb2R1Y3RzIjpbeyJQcm9kdWN0SWQiOiI2MTcyYmVhMC1kOGFhLTRhZWEtODk2OC0wOTg1NzgxZDUyZmUiLCJNYXJrZXRwbGFjZUlkIjoxMDAwMCwiUHJvZHVjdFN0YXR1c0tleSI6ImFjdGl2ZSJ9XSwibWZhRXhwaXJhdGlvbiI6IjE3NDUyMzQ2NDIiLCJwYXJ0bmVySWQiOiIiLCJzaWQiOiI2REJDOTc4ODZDMDU5QUQyNzQ4REFBMjc4NjdBNDA5MiJ9.eRr3W7e1OufuUrABm1o8Tc_GQf5rWVhSOJexMDwmMsWWt0H7EiP2vln6fLBoYj3qGknDjbMdhdxsqbeWrnzoR0Ju04presP9IqaDvzyOVHg1Ld5Q-OsadeGL08IC-OnA3W8XCmatqos0q4Eys2zgO6mFBLJA7qXL8Fmro2aMhDvxVwi54kJ66MUwAffS2Af0x77Ym0pw9-BENFzx3j7Y-fXDCDVyVWqZw5s1uWOfxzvnwnDm2-sqm7CU2Inj6awBrjK3PWwMUatwDNxmvS7_KP1wUmaRxypnMaMjjoGdEO-nwJ4vcAfOc0ZwaQvqKryGIqnTY9JfoRJWC-mNF2Kekw',
            'content-type': 'application/json',
            'origin': origin,
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

    def set_authorization_header(self, token):
        self.base_headers['authorization'] = f"Bearer {token}"

    def fetch_loads(self, state):
        loads_response = self.post("https://bff.centraldispatch.com/listing-search/api/open-search",  # type: ignore
                                    payload={
                                        'vehicleCount': {
                                            'min': 1,
                                            'max': None,
                                        },
                                        'postedWithinHours': None,
                                        'tagListingsPostedWithin': 2,
                                        'trailerTypes': ['OPEN'],
                                        'paymentTypes': [],
                                        'vehicleTypes': ['CAR', 'VAN', 'SUV', 'MOTORCYCLE', 'PICKUP'],
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
                                        'locations': [{
                                            'state': state,
                                            'scope': 'Pickup',
                                        },],
                                    })
        return loads_response