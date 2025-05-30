import sys
import os
# Add the project root directory to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(project_root)
# Keep the original append for backward compatibility
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from geoalchemy2.elements import WKTElement
import logging
from resources.models import LoadModel, get_db
from selenium.webdriver.common.by import By
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_driver import SeleniumDriver
from dotenv import load_dotenv
from selenium_agency.otp_verifiers.gmail_verify import get_otp_from_gmail_super
from selenium_agency.api.super_api_client import SuperAPIClient
from selenium_agency.cache.super_cache import SuperCacheService
import json
from api.handlers import GraphhopperHandler, BulkRequestHandler

script_dir = os.path.dirname(os.path.abspath(__file__))
log_file_path = os.path.join(os.path.dirname(script_dir), 'logs', 'super_agent.log')

# Configure logging
logging.basicConfig(
    filename=log_file_path,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class SuperInteractor:
    def __init__(self, selenium_driver=None, api_client=None, cache_service=None, db_session=None, bulk_request_handler=None):
        self.__selenium_driver = selenium_driver
        if self.__selenium_driver is None:
            self.__selenium_driver = SeleniumDriver()
        self.__driver = self.__selenium_driver.get_driver()
        self.__api_client = api_client
        if self.__api_client is None:
            self.__api_client = SuperAPIClient()
        self.__cache_service = cache_service
        self.current_page = 0
        self.__total_records = 0
        self.__record_count_per_page = 0
        self.__db_Session = db_session
        self.__in_between_delay = 1
        self.__bulk_request_handler = bulk_request_handler

    def get_token(self):
        if not self.__driver:
            return None
        cookies = self.__driver.get_cookies()
        user_token = None
        for cookie in cookies:
            if cookie['name'] == 'userToken':
                user_token = cookie['value']
                break
        if user_token:
            logger.info(f"User token found: {user_token}")
            self.__cache_service.set_token(user_token) # type: ignore
            return user_token
        else:
            logger.info("User token not found in cookies")
            return None
            
    def format_pickup_location(self, pickup_data):
        if not pickup_data or not pickup_data.get('venue'):
            return ''
        venue = pickup_data['venue']
        address_part = f"{venue.get('metro_area', '')}, " if venue.get('metro_area') else ""
        return f"{address_part}{venue.get('city', '')}, {venue.get('state', '')} {venue.get('zip', '')}"

    def format_delivery_location(self, delivery_data):
        if not delivery_data or not delivery_data.get('venue'):
            return ''
        venue = delivery_data['venue']
        address_part = f"{venue.get('metro_area', '')}, " if venue.get('metro_area') else ""
        return f"{address_part}{venue.get('city', '')}, {venue.get('state', '')} {venue.get('zip', '')}"

    def format_and_get_load_model(self, load):
        # If the load comes wrapped in a container object, get the main load object
        load_data = load.get('load') if 'load' in load else load
        if not load_data:
            return None

        instructions = load_data.get('instructions', '')
        brokerage = load_data.get('shipper', '').get('name', '')
        # Calculate total weight and get vehicle count from the load
        total_weight = 0
        vehicles = load_data.get('vehicles', [])
        for vehicle in vehicles:
            # Super Dispatch might have weight in different formats based on vehicle type
            weight = 0
            if isinstance(vehicle, dict):
                # Try to extract weight information if available
                weight = float(vehicle.get('weight', 0))
            total_weight += weight
            
        load_model_instance = LoadModel(
            external_load_id=load_data.get('guid', ''),
            brokerage="Super Dispatch",
            pickup_location=load.get('pickup_location'),
            delivery_location=load.get('delivery_location'),
            pickup_points=load.get('pickup_points'),
            delivery_points=load.get('delivery_points'),
            price=str(load_data.get('price', '')),
            milage=float(load_data.get('distance_meters', 0)) / 1609.34,  # Convert meters to miles
            is_operational=not any(vehicle.get('is_inoperable', False) for vehicle in load_data.get('vehicles', [])),
            contact_phone=(load_data.get('shipper') or {}).get('contact_phone', ''),
            notes=instructions,
            loadboard_source="super_dispatch",
            created_at=load_data.get('created_at', ''),
            date_ready=load_data.get('pickup', {}).get('scheduled_at', ''),
            n_vehicles=len(vehicles),
            weight=float(total_weight)
        )

        return load_model_instance
        
    def batch_save_loads(self, loads, in_between_delay=1):
        print("Initiating batch request")
        if len(loads) > 0:
            bulk_locations = []
            for load in loads:
                pickup_location = self.format_pickup_location(load.get('load').get('pickup', {}))
                delivery_location = self.format_delivery_location(load.get('load').get('delivery', {}))
                load['pickup_location'] = pickup_location
                load['delivery_location'] = delivery_location
                bulk_locations.append({"pickup_location": pickup_location, "delivery_location": delivery_location})

            bulk_coordinates = self.__bulk_request_handler.post("/bulk_geocode", payload=bulk_locations).json() # type: ignore

            print("received bulk coordinates")
            for index, bulk_coordinate in enumerate(bulk_coordinates):
                pickup_location_coordinate = bulk_coordinate.get('pickup_coordinates')
                delivery_location_coordinate = bulk_coordinate.get('delivery_coordinates')
                pickup_points = WKTElement(f'POINT({pickup_location_coordinate[0]} {pickup_location_coordinate[1]})') if pickup_location_coordinate else None
                delivery_points = WKTElement(f'POINT({delivery_location_coordinate[0]} {delivery_location_coordinate[1]})') if delivery_location_coordinate else None
                loads[index]['pickup_points'] = pickup_points
                loads[index]['delivery_points'] = delivery_points
                
            load_model_instances = [
                self.format_and_get_load_model(load) for load in loads
            ]
            # Bulk insert
            if self.__db_Session is None:
                raise ConnectionRefusedError("Database session is not initialized.")
            self.__db_Session.bulk_save_objects(load_model_instances)
            self.__db_Session.commit()
            time.sleep(in_between_delay)
            logger.info("Loads inserted into DB")
    
    def fetch_loads(self, page=0):
        if self.__cache_service is None:
            raise FileExistsError("Cache service is not initialized.")
        token = self.__cache_service.get_token()
        if self.__api_client is None:
            raise ConnectionError("API client is not initialized.")
        self.__api_client.set_authorization_header(token)
        loads_response = self.__api_client.post("/internal/v3/loads/search", 
                            token=token, 
                            payload={},
                            params={"page": page, "size": 100})
        
        if loads_response.status_code == 401:
            self.__cache_service.clear_all()
            return None
        
        return loads_response.json()['data']
    
    def deduplicate_loads(self, loads):
        if not loads:
            return []
            
        # First filter out loads already in the database by ID
        existing_load_ids = {id_tuple[0] for id_tuple in self.__db_Session.query(LoadModel.external_load_id).all()} # type: ignore
        loads = [load for load in loads if load.get('load').get('guid') not in existing_load_ids]
        logger.info(f"Loads after filtering existing IDs: {len(loads)}")
        print(f"Loads after filtering existing IDs: {len(loads)}")
        
        # Filter loads by distance and price criteria
        filtered_loads = []
        for load in loads:
            distance_meters = load.get('load').get('distance_meters', 0)
            if distance_meters is None:
                continue

            if distance_meters <= 0 or distance_meters >= 2000000 or load.get('load', {}).get('price', 0) >= 3000:
                continue
                
            filtered_loads.append(load)
            
        logger.info(f"Filtered loads after basic criteria: {len(filtered_loads)}")
        print(f"Filtered loads after basic criteria: {len(filtered_loads)}")
        
        if self.__db_Session is None:
            raise ConnectionRefusedError("Database session is not initialized.")
        # Fetch all existing loads once to use for duplicate detection
        existing_loads = self.__db_Session.query(
            LoadModel.price, 
            LoadModel.milage, 
            LoadModel.pickup_location, 
            LoadModel.delivery_location
        ).all()
        
        # Create a set of tuples for faster lookup
        existing_loads_set = {
            (load.price, load.milage, load.pickup_location, load.delivery_location)
            for load in existing_loads
        }
        
        # Check for duplicates in database based on price, distance, pickup and delivery locations
        non_duplicate_loads = []
        for load in filtered_loads:
            pickup_venue = load.get('load', {}).get('pickup', {}).get('venue', {})
            delivery_venue = load.get('load', {}).get('delivery', {}).get('venue', {})
            
            pickup_location = f"{pickup_venue.get('city', '')}, {pickup_venue.get('state', '')} {pickup_venue.get('zip', '')}"
            delivery_location = f"{delivery_venue.get('city', '')}, {delivery_venue.get('state', '')} {delivery_venue.get('zip', '')}"
            
            price = str(load.get('load', {}).get('price', 0))
            distance = float(load.get('load', {}).get('distance_meters', 0)) / 1609.34  # Convert meters to miles
            
            # Check against in-memory set of loads - more efficient than individual database queries
            similar_load_exists = False
            for existing_price, existing_milage, existing_pickup, existing_delivery in existing_loads_set:
                if (existing_price == price and
                    existing_pickup == pickup_location and
                    existing_delivery == delivery_location and
                    existing_milage * 0.98 <= distance <= existing_milage * 1.02):
                    similar_load_exists = True
                    break
            
            if not similar_load_exists:
                load['pickup_location'] = pickup_location
                load['delivery_location'] = delivery_location
                non_duplicate_loads.append(load)
        
        logger.info(f"New loads to process after deduplication: {len(non_duplicate_loads)}")
        print(f"New loads to process after deduplication: {len(non_duplicate_loads)}")
        
        return non_duplicate_loads