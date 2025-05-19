import json
import time
import logging
import sys
import os

# Add the project root directory to sys.path
project_root = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', '..'))
sys.path.append(project_root)
# Keep the original append for backward compatibility
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


script_dir = os.path.dirname(os.path.abspath(__file__))
log_file_path = os.path.join(os.path.dirname(
    script_dir), 'logs', 'central_agent.log')

# Configure logging
logging.basicConfig(
    filename=log_file_path,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class CentralInteractor:
    def __init__(self,
                 api_client=None, 
                 deduplicator=None, 
                 db_worker=None, 
                 token_worker=None):
        self.__api_client = api_client
        self.__db_worker = db_worker
        self.deduplicator = deduplicator
        self.__token_worker = token_worker
    
    def token_exists(self):
        return self.__token_worker.token_exists()

    def set_token(self):
        self.__token_worker.set_token()

    def deduplicate_loads(self, loadsParam):
        #db_loads = self.__fetch_db_loads()
        db_loads = self.__db_worker.fetch_db_loads()
        if db_loads is None or len(db_loads) == 0:
            logger.error("Failed to fetch existing loads from the database.")
            print("Failed to fetch existing loads from the database or it is empty.")
            return []

        deduplicated_loads = self.deduplicator.deduplicate_loads(target_loads=loadsParam,
                                                                db_loads=db_loads)
        
        print(f"deduplicated loads count: {len(deduplicated_loads)}")
        return deduplicated_loads
    
    def filter_loads(self, loads):
          # 1. Filter by existing IDs from the database
        # Ensure loadsParam is iterable, default to empty list if None
        if loadsParam is None:
            loadsParam = []

        # 2. Filter by distance and price criteria
        filtered_loads = []
        for load_item in loads:
            distance = load_item.get('distance')
            price_data = load_item.get('price', {})
            price_total = price_data.get('total', 0) if isinstance(price_data, dict) else 0

            if distance is None:
                logger.warning(f"Skipping load {load_item.get('id')} due to missing distance.")
                continue
            
            if not isinstance(distance, (int, float)):
                logger.warning(f"Skipping load {load_item.get('id')} due to non-numeric distance: {distance}")
                continue
            if not isinstance(price_total, (int, float)):
                logger.warning(f"Skipping load {load_item.get('id')} due to non-numeric price_total: {price_total}")
                continue

            if distance <= 0.0 or distance >= 2000.0 or price_total >= 3000.0:
                continue
            filtered_loads.append(load_item)

        print(f"Filtered loads count: {len(filtered_loads)}")
        return filtered_loads
    

    def save_loads_to_db(self, non_duplicate_loads):
        self.__db_worker.save_loads(non_duplicate_loads)

    def fetch_loads(self, state):
        token = self.__token_worker.get_token()
        self.__api_client.set_authorization_header(token)
        
        try:
            loads_response = self.__api_client.fetch_loads(state)
            response_json = loads_response.json()
            loads = response_json['items']
            if loads is None:
                print("Loads is None")
                raise ValueError("Loads is None")
            time.sleep(30)
            return loads
        except Exception as e:
            print(f"Error fetching loads: {e}")
            self.__token_worker.remove_token()


