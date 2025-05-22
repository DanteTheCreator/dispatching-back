import json
import time

class CentralTokenWorker:
    def __init__(self, cache_service=None, driver=None):
        self.__driver = driver
        self.__cache_service = cache_service
        pass 

    def match_tokens(self):
        if self.__cache_service.token_exists():
            cache_token = self.__cache_service.get_token()
            remote_token = self.get_token_remotely()

            # try again one more time if remote token is None
            if remote_token is None:
                print("trying to fetch remote token one more time...")
                time.sleep(5)
                remote_token = self.get_token_remotely()

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

             # try again one more time if remote token is None
            if remote_token is None:
                print("trying to fetch remote token one more time...")
                time.sleep(5)
                remote_token = self.get_token_remotely()

                
            if remote_token:
                self.__cache_service.set_token(remote_token)

    def token_exists(self):
        return self.__cache_service.token_exists()
    
    def token_is_valid(self):
        if self.__cache_service.token_exists():
            token = self.__cache_service.get_token()
            if token:
                remote_token = self.get_token_remotely()
                return token == remote_token
        return False
    
    def get_token(self):
        if self.__cache_service is not None:
            token = self.__cache_service.get_token()
            print(f"Token retrieved from cache")
            return token
        else:
            print("Cache service is not initialized.")
            return None
    
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