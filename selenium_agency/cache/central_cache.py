from selenium_agency.cache.cache_service import CacheService
from datetime import datetime, timedelta

class CentralCacheService(CacheService):
    def __init__(self):
        super().__init__("central_dispatch")
        self.TOKEN_KEY = "central_token"
        self.LOADS_KEY = "central_loads"

    def token_exists(self):
        return self.get(self.TOKEN_KEY) is not None

    def set_token(self, token):
        """Store token with expiration time"""
        self.set(self.TOKEN_KEY, token)


    def get_token(self):
        """Get token if it exists and is not expired"""
        token = self.get(self.TOKEN_KEY)
        
        if not token:
            return None
        
        return token
        
    def remove_token(self):
        """Remove token and its expiry from cache"""
        self.remove(self.TOKEN_KEY)

    def cache_loads(self, loads):
        """Store loads data with timestamp"""
        data = {
            "timestamp": datetime.now().isoformat(),
            "loads": loads
        }
        self.set(self.LOADS_KEY, data)

    def get_cached_loads(self, max_age_minutes=30):
        """Get cached loads if they exist and are not older than max_age_minutes"""
        cached_data = self.get(self.LOADS_KEY)
        if not cached_data:
            return None

        try:
            timestamp = datetime.fromisoformat(cached_data["timestamp"])
            if datetime.now() - timestamp > timedelta(minutes=max_age_minutes):
                return None
            return cached_data["loads"]
        except Exception as e:
            print(f"Error retrieving cached loads: {e}")
            return None

    def clear_all(self):
        """Clear all Super Dispatch related cache"""
        self.clear()