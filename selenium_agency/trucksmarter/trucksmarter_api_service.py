import os
import sys

# directory reach
directory = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(directory)

# setting path
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# importing (use only one import style)
from selenium_agency.network_service import NetworkService

class TrucksmarterServiceApi(NetworkService):
    API_BASE_URL = "https://api.trucksmarter.com"
    VERIFY = False
    USER_AGENT = "PostmanRuntime/7.43.0"