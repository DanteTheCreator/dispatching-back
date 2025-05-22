import time

class CentralInteractor:
    def __init__(self,
                 api_client=None, 
                 deduplicator=None, 
                 db_worker=None, 
                 token_worker=None):
        self.__api_client = api_client
        self.__db_worker = db_worker
        self.__deduplicator = deduplicator
        self.__token_worker = token_worker
    
    def token_exists(self):
        return self.__token_worker.token_exists()

    def set_token(self):
        print("setting token...")
        self.__token_worker.match_tokens()

    def remove_token(self):
        print("removing token...")
        self.__token_worker.remove_token()

    def deduplicate_loads(self, loadsParam):
        #db_loads = self.__fetch_db_loads()
        db_loads = self.__db_worker.fetch_db_loads()
        if db_loads is None or len(db_loads) == 0:
            print("Failed to fetch existing loads from the database or it is empty.")
            return loadsParam
        
        print(f"Fetched {len(db_loads)} existing loads from the database.")

        deduplicated_loads = self.__deduplicator.deduplicate_loads(target_loads=loadsParam,
                                                                db_loads=db_loads)
        
        print(f"deduplicated loads count: {len(deduplicated_loads)}")
        return deduplicated_loads
    
    def filter_loads(self, loads):
        print(f"Filtering {len(loads)} loads.")
          # 1. Filter by existing IDs from the database
        # Ensure loadsParam is iterable, default to empty list if None
        if loads is None:
            print("No loads to filter.")
            loads = []

        # 2. Filter by distance and price criteria
        filtered_loads = []
        for load_item in loads:
            distance = load_item.get('distance')
            price_data = load_item.get('price', {})
            price_total = price_data.get('total', 0) if isinstance(price_data, dict) else 0

            if distance is None:
                print(f"Skipping load {load_item.get('id')} due to missing distance.")
                continue
            
            if not isinstance(distance, (int, float)):
                print(f"Skipping load {load_item.get('id')} due to non-numeric distance: {distance}")
                continue
            if not isinstance(price_total, (int, float)):
                print(f"Skipping load {load_item.get('id')} due to non-numeric price_total: {price_total}")
                continue

            if distance <= 0.0 or distance >= 2000.0 or price_total >= 3000.0:
                continue
            filtered_loads.append(load_item)

        print(f"Filtered loads count: {len(filtered_loads)}")
        return filtered_loads
    

    def save_loads_to_db(self, non_duplicate_loads):
        self.__db_worker.save_loads_to_db(non_duplicate_loads)

    def fetch_loads(self, state, recursion_count=0):
        print(f"Recursion count: {recursion_count}")
        print(f"Fetching loads for state: {state}")
        recursion_count += 1
        token = self.__token_worker.get_token()
        self.__api_client.set_authorization_header(token)
        
        try:
            loads_response = self.__api_client.fetch_loads(state)
            response_json = loads_response.json()
            loads = response_json['items']
            print(f"{len(loads)} loads fetched successfully")
            time.sleep(30)
            return loads
        except Exception as e:
            # Check specifically for 401 Unauthorized error
            if hasattr(e, 'response') and e.response.status_code == 401:
                print("Authentication failed (401 Unauthorized)")
                print("Removing token and relogging in 10 minutes...")
                time.sleep(10)
                self.__token_worker.match_tokens()
                time.sleep(10)
                if recursion_count < 3:
                    return self.fetch_loads(state, recursion_count)
                else:
                    print("Max retries reached. Removing token. Relogging...")
                    self.remove_token()
            else:
                # Handle other exceptions
                print(f"Error fetching loads: {e}")
                print("Retrying in 10 seconds...")
                time.sleep(10)
                if recursion_count < 3:
                    return self.fetch_loads(state, recursion_count)
                else:
                    print("Max retries reached. Removing token. Relogging...")
                    self.remove_token()



