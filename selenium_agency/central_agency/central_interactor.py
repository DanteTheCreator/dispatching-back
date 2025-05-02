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
from selenium_agency.otp_verifiers.gmail_verify import get_otp_from_gmail_central
from selenium_agency.api.central_api_client import CentralAPIClient
from selenium_agency.cache.central_cache import CentralCacheService
import json

script_dir = os.path.dirname(os.path.abspath(__file__))
log_file_path = os.path.join(os.path.dirname(script_dir), 'logs', 'central_agent.log')

# Configure logging
logging.basicConfig(
    filename=log_file_path,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class CentralInteractor:
    def __init__(self, selenium_driver=None, api_client=None, cache_service=None, db_session=None):
        self.__selenium_driver = selenium_driver
        self.__driver = self.__selenium_driver.get_driver()
        self.__api_client = api_client
        self.__cache_service = cache_service
        self.current_page = 0
        self.__total_records = 0
        self.__record_count_per_page = 0
        self.__db_Session = db_session
        self.__in_between_delay = 1  # Adding the missing attribute with a default value

    def set_token(self):
        if not self.__driver:
            return None
        # Execute JavaScript to get token from localStorage
        user_token = self.__driver.execute_script(
                "return window.localStorage.getItem('oidc.user:https://id.centraldispatch.com:single_spa_prod_client');"
            )
        try:
            user_token = json.loads(user_token)['access_token'] if user_token else None
        except json.JSONDecodeError:
            user_token = None

        if user_token is not None:
            self.__cache_service.set_token(user_token)
            return user_token
        else:
            logger.info("User token not found in localStorage")
            return None
        
    def deduplicate_loads(self, loadsParam):
        existing_load_ids = {id_tuple[0] for id_tuple in self.__db_Session.query(LoadModel.external_load_id).all()}
        loads = [load for load in loadsParam if str(load.get('id')) not in existing_load_ids]
        logger.info(f"Loads after filtering existing IDs: {len(loads)}")
        print(f"Loads after filtering existing IDs: {len(loads)}")
        
        # Filter loads by distance and price criteria
        filtered_loads = []
        for load in loads:
            distance = load.get('distance')
            if distance is None:
                continue

            if distance <= 0 or distance >= 2000 or load.get('price', {}).get('total', 0) >= 3000:
                continue
                
            filtered_loads.append(load)
            
        logger.info(f"Filtered loads after basic criteria: {len(filtered_loads)}")
        print(f"Filtered loads after basic criteria: {len(filtered_loads)}")
        
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
            pickup_location = f"{load['origin']['city']}, {load['origin']['state']} {load['origin']['zip']}"
            delivery_location = f"{load['destination']['city']}, {load['destination']['state']} {load['destination']['zip']}"
            
            price = str(load['price']['total'])
            distance = float(load.get('distance', 0))
            
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
                non_duplicate_loads.append(load)
        
        logger.info(f"New loads to process after deduplication: {len(non_duplicate_loads)}")
        print(f"New loads to process after deduplication: {len(non_duplicate_loads)}")
        return non_duplicate_loads
    
    def __format_and_get_load_model(self, load):
        if not load:
            return None

        try:
            pickup_location = f"{load['origin']['city']}, {load['origin']['state']} {load['origin']['zip']}"
            delivery_location = f"{load['destination']['city']}, {load['destination']['state']} {load['destination']['zip']}"

            pickup_coordinates = [load['origin']['geoCode']
                                ['longitude'], load['origin']['geoCode']['latitude']]
            delivery_coordinates = [load['destination']['geoCode']
                                    ['longitude'], load['destination']['geoCode']['latitude']]
        except KeyError as e:
            logger.error(f"KeyError: {e} in load data: {load}")
            print(f"KeyError: {e} in load data: {load}")
            return None  # This will cause the load to be skipped when filtered in __start_filling_db_cycle

        # Convert coordinates to WKT format
        pickup_points = WKTElement(
            f'POINT({pickup_coordinates[0]} {pickup_coordinates[1]})') if pickup_coordinates else None
        delivery_points = WKTElement(
            f'POINT({delivery_coordinates[0]} {delivery_coordinates[1]})') if delivery_coordinates else None

        coordinates_note = f"Pickup coordinates: {pickup_coordinates}, Delivery coordinates: {delivery_coordinates}"
        instructions = load.get('additionalInfo', '')
        combined_notes = f"{instructions}\n{coordinates_note}"
        
        # Calculate total weight from vehicles
        total_weight = 0
        for vehicle in load.get('vehicles', []):
            if vehicle and vehicle.get('shippingSpecs') and vehicle.get('shippingSpecs').get('weight'):
                total_weight += vehicle.get('shippingSpecs').get('weight', 0)

        load_model_instance = LoadModel(
            external_load_id=str(load.get('id', '')),
            brokerage="Central Dispatch",
            pickup_location=pickup_location,
            delivery_location=delivery_location,
            pickup_points=pickup_points,
            delivery_points=delivery_points,
            price=str(load['price']['total']),
            milage=float(load.get('distance', 0)),
            is_operational=not load.get('hasInOpVehicle', False),
            contact_phone=load['shipper'].get('phone', ''),
            notes=combined_notes,
            loadboard_source="central_dispatch",
            created_at=load.get('createdDate', ''),
            date_ready=load.get('availableDate', ''),
            n_vehicles=len(load.get('vehicles', [])),
            weight=float(total_weight)
        )
        
        return load_model_instance
    
    def save_loads_to_db(self, non_duplicate_loads):
        if len(non_duplicate_loads) == 0:
            logger.info("No new loads to process, every load is already in the database")
            print("No new loads to process, every load is already in the database")
            return
        
        if len(non_duplicate_loads) > 0:
            load_model_instances = [
                model for model in (self.__format_and_get_load_model(load) for load in non_duplicate_loads)
                if model is not None  # Filter out None values that result from KeyError
            ]
            
            if load_model_instances:  # Only proceed if there are valid models to save
                # Bulk insert
                self.__db_Session.bulk_save_objects(load_model_instances)
                self.__db_Session.commit()
                time.sleep(self.__in_between_delay)
                logger.info(f"Inserted {len(load_model_instances)} loads into DB")
            else:
                logger.info("No valid loads to insert into DB")
        
    def fetch_loads(self):
        token = self.__cache_service.get_token()
        self.__api_client.set_authorization_header(token)
        try:
            loads_response = self.__api_client.post("https://bff.centraldispatch.com/listing-search/api/open-search",
                                                    payload={
                                                        'vehicleCount': {
                                                            'min': 1,
                                                            'max': None,
                                                        },
                                                        'postedWithinHours': None,
                                                        'tagListingsPostedWithin': 2,
                                                        'trailerTypes': [],
                                                        'paymentTypes': [],
                                                        'vehicleTypes': [],
                                                        'operability': 'All',
                                                        'minimumPaymentTotal': None,
                                                        'readyToShipWithinDays': None,
                                                        'minimumPricePerMile': None,
                                                        'offset': self.current_page * 500,
                                                        'limit': 500,
                                                        'sortFields': [
                                                            {
                                                                'name': 'PICKUP',
                                                                'direction': 'ASC',
                                                            },
                                                            {
                                                                'name': 'DELIVERYMETROAREA',
                                                                'direction': 'ASC',
                                                            },
                                                        ],
                                                        'shipperIds': [],
                                                        'desiredDeliveryDate': None,
                                                        'displayBlockedShippers': False,
                                                        'showPreferredShippersOnly': False,
                                                        'showTaggedOnTop': False,
                                                        'marketplaceIds': [],
                                                        'averageRating': 'All',
                                                        'requestType': 'Open',
                                                        'locations': [],
                                                    })
            self.current_page += 1
            print(f"Page: {self.current_page}")

            response_json = loads_response.json()
            loads = response_json['items']
            total_records = response_json['totalRecords']
            count = response_json['count']

            if self.__record_count_per_page == 0 and self.__total_records == 0:
                self.__record_count_per_page = count
                self.__total_records = total_records

                logger.info(f"Total records: {self.__total_records}, Records per page: {self.__record_count_per_page}")
                print(f"Total records: {self.__total_records}, Records per page: {self.__record_count_per_page}")

            print("Page: ", self.current_page, "Total records: ", self.__total_records, "Records per page: ", self.__record_count_per_page)
            print(self.current_page >= (self.__total_records / self.__record_count_per_page) + 1)
            if (self.current_page >= (self.__total_records / self.__record_count_per_page) + 1):
                logger.info("No more pages to process")
                print("No more pages to process")
                self.current_page = 0
                self.__total_records = 0
                self.__record_count_per_page = 0
                time.sleep(200)


            return loads
        except Exception as e:
            logger.error(f"Error fetching loads: {e}")
            print(f"Error fetching loads: {e}")
            # Check if the exception contains status code information
            if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                status_code = e.response.status_code
                if status_code == 401 or status_code == 403:
                    print(f"Authentication error: status code {status_code}")
                    self.__cache_service.clear_all()
                    time.sleep(self.__in_between_delay)
                    logger.info("Authentication failed, will re-login")
                    print("Authentication failed, will re-login")
            return
