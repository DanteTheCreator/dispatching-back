from cache_service import CacheService
from datetime import datetime, timedelta

class CentralCacheService(CacheService):
    def __init__(self):
        super().__init__("central_dispatch")
        self.TOKEN_KEY = "central_token"
        self.LOADS_KEY = "central_loads"
        self.TOKEN_EXPIRY_KEY = "central_token_expiry"
        self.TOKEN_EXPIRY_HOURS = 23  # Set token expiry slightly less than 24h

    def token_exists(self):
        """Check if a valid token exists in cache
        
        Returns:
            bool: True if valid token exists, False otherwise
        """
        return self.get_token() is not None

    def set_token(self, token):
        """Store token with expiration time"""
        expiry = datetime.now() + timedelta(hours=self.TOKEN_EXPIRY_HOURS)
        self.set(self.TOKEN_KEY, token)
        self.set(self.TOKEN_EXPIRY_KEY, expiry.isoformat())


    def get_token(self):
        """Get token if it exists and is not expired"""
        token = self.get(self.TOKEN_KEY)
        expiry_str = self.get(self.TOKEN_EXPIRY_KEY)
        
        if not token or not expiry_str:
            return None

        try:
            expiry = datetime.fromisoformat(expiry_str)
            if datetime.now() > expiry:
                self.remove(self.TOKEN_KEY)
                self.remove(self.TOKEN_EXPIRY_KEY)
                return None
            return token
        except Exception as e:
            print(f"Error parsing token expiry: {e}")
            return None

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