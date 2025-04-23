import json
import os

class CacheService:
    def __init__(self, cache_key):
        self.cache_key = cache_key
        # Create tmp directory in the same folder as this script
        self.tmp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tmp")
        if not os.path.exists(self.tmp_dir):
            os.makedirs(self.tmp_dir)
        self.cache_file = os.path.join(self.tmp_dir, f"{cache_key}.json")
        self.cache = self._load_cache()

    def _load_cache(self):
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"Error loading cache: {e}")
            return {}

    def _save_cache(self):
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f)
        except Exception as e:
            print(f"Error saving cache: {e}")

    def get(self, key):
        return self.cache.get(key, None)

    def set(self, key, data):
        self.cache[key] = data
        self._save_cache()

    def remove(self, key):
        if key in self.cache:
            del self.cache[key]
            self._save_cache()

    def clear(self):
        self.cache = {}
        if os.path.exists(self.cache_file):
            os.remove(self.cache_file)