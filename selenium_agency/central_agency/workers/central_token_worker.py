import json


class CentralTokenWorker:
    def __init__(self, cache_service=None, driver=None):
        self.__driver = driver
        self.__cache_service = cache_service
        pass 

    def match_tokens(self):
        if self.__cache_service.token_exists():
            cache_token = self.__cache_service.get_token()
            remote_token = self.get_token_remotely()
            if cache_token and remote_token:
                if cache_token == remote_token:
                    pass
                else:
                    print("Tokens do not match.")
                    print("Updating token in cache...")
                    self.__cache_service.remove_token()
                    self.__cache_service.set_token(remote_token)
        else:
            print("Token does not exist in cache.")
            print("Fetching token remotely...")
            remote_token = self.get_token_remotely()
            if remote_token:
                self.__cache_service.set_token(remote_token)

    def token_exists(self):
        return self.__cache_service.token_exists()
    
    def get_token(self):
        if not self.__cache_service:
            return None
        token = self.__cache_service.get_token()
        if token is None:
            print("Token not found in cache service.")
            print("Fetching token remotely...")
            token = self.get_token_remotely()
            if token:
                self.__cache_service.set_token(token)
                return token
            else:
                print("Failed to fetch token remotely.")
                return None
        return token
    
    def get_token_remotely(self):
        if not self.__driver:
            print("Driver is not initialized.")
            return None

        try:
            user_token = self.__driver.execute_script(
                "return window.localStorage.getItem('oidc.user:https://id.centraldispatch.com:single_spa_prod_client');"
            )
            try:
                user_token = json.loads(user_token)[
                    'access_token'] if user_token else None
                print("User token retrieved from localStorage.")
                print(f"User token: {user_token}")
            except json.JSONDecodeError:
                print("Error decoding JSON from localStorage.")
                user_token = None
        except Exception as e:
            print(f"Error accessing localStorage: {e}")
            user_token = None

        return user_token
        
    def remove_token(self):
        if self.__cache_service is not None:
            self.__cache_service.remove_token()
            print("Token removed from cache service.")
        else:
            print("Cache service is not initialized.")