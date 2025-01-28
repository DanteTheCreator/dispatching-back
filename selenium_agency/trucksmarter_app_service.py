from network_service import NetworkService

class TrucksmarterServiceApp(NetworkService):
    API_BASE_URL = "https://app.trucksmarter.com"
    VERIFY = False
    USER_AGENT = "PostmanRuntime/7.43.0"