import json


class CentralTokenWorker:
    def __init__(self, cache_service=None, driver=None):
        self.__driver = driver
        self.__cache_service = cache_service
        pass 

    def token_exists(self):
        return self.__cache_service.token_exists()
    
    def get_token(self):
        if not self.__cache_service:
            return None
        token = self.__cache_service.get_token()
        if token is None:
            print("Token not found in cache service.")
            return None
        return token

    def set_token(self):
        if not self.__driver:
            return None
        # Check current URL before accessing localStorage
        current_url = self.__driver.current_url
        if not current_url.startswith("https://id.centraldispatch.com"):
            print(f"Cannot access localStorage: current URL is {current_url}")
            return None
        # Execute JavaScript to get token from localStorage
        try:
            user_token = self.__driver.execute_script(
                "return window.localStorage.getItem('oidc.user:https://id.centraldispatch.com:single_spa_prod_client');"
            )
            try:
                user_token = json.loads(user_token)[
                    'access_token'] if user_token else None
            except json.JSONDecodeError:
                user_token = None
        except Exception as e:
            print(f"Error accessing localStorage: {e}")
            user_token = None

        if user_token is not None and self.__cache_service is not None:
            self.__cache_service.set_token(user_token)
            return user_token
        else:
            print("User token not found in localStorage")
            return None
        
    def remove_token(self):
        if self.__cache_service is not None:
            self.__cache_service.remove_token()
            print("Token removed from cache service.")
        else:
            print("Cache service is not initialized.")