import json
from selenium_driver import SeleniumDriver
from selenium.webdriver.support import expected_conditions as EC
import time
import logging
from geoalchemy2.elements import WKTElement
import sys
import os
from resources.models import LoadModel
from selenium_agency.utils.array_deduplicator import ArrayDeduplicator
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
    def __init__(self, selenium_driver=None, api_client=None, cache_service=None, db_session=None):
        self.__selenium_driver = selenium_driver
        if self.__selenium_driver is None:
            self.__selenium_driver = SeleniumDriver()
        self.__driver = self.__selenium_driver.get_driver()
        self.__api_client = api_client
        self.__cache_service = cache_service
        self.current_page = 0
        self.__db_Session = db_session
        self.__in_between_delay = 1  # Adding the missing attribute with a default value
        self.__array_deduplicator = ArrayDeduplicator()

    def __fetch_db_loads(self):
        if self.__db_Session is None:
            logger.error("Database session is not initialized.")
            print("Database session is not initialized.")
            return []

        existing_loads = self.__db_Session.query(
            LoadModel.external_load_id,
            LoadModel.price,
            LoadModel.milage,
            LoadModel.pickup_location,
            LoadModel.delivery_location
        ).all()

        # Convert query results to dictionaries with proper keys
        existing_loads_dicts = [
            {
                'external_load_id': row[0],
                'price': row[1],
                'milage': row[2],
                'pickup_location': row[3],
                'delivery_location': row[4]
            }
            for row in existing_loads
        ]

        return existing_loads_dicts
    
    def __attributes_compare_callback(target, base, get_recursive):
            # Compare the target and base objects based on the specified criteria
            target_price = get_recursive(target, 'price')
            base_price = get_recursive(base, 'price')

            target_origin = get_recursive(target, 'origin')
            target_destination = get_recursive(target, 'destination')

            target_zip = get_recursive(target_origin, 'zip')
            target_city = get_recursive(target_origin, 'city')
            target_state = get_recursive(target_origin, 'state')

            target_pickup_location = f"{target_city}, {target_state} {target_zip}"

            target_zip_dest = get_recursive(target_destination, 'zip')
            target_city_dest = get_recursive(target_destination, 'city')
            target_state_dest = get_recursive(target_destination, 'state')

            target_delivery_location = f"{target_city_dest}, {target_state_dest} {target_zip_dest}"

            target_milage = get_recursive(target, 'milage')
            base_milage = get_recursive(base, 'milage')

            base_pickup_location = get_recursive(base, 'pickup_location')
            base_delivery_location = get_recursive(base, 'delivery_location')

            return (target_price == base_price and
                    target_pickup_location == base_pickup_location and
                    target_delivery_location == base_delivery_location and
                    target_milage == base_milage)

    def set_token(self):
        if not self.__driver:
            return None
        # Execute JavaScript to get token from localStorage
        user_token = self.__driver.execute_script(
            "return window.localStorage.getItem('oidc.user:https://id.centraldispatch.com:single_spa_prod_client');"
        )
        try:
            user_token = json.loads(user_token)[
                'access_token'] if user_token else None
        except json.JSONDecodeError:
            user_token = None

        if user_token is not None and self.__cache_service is not None:
            self.__cache_service.set_token(user_token)
            return user_token
        else:
            logger.info("User token not found in localStorage")
            return None
        
    def remove_token(self):
        if self.__cache_service is not None:
            self.__cache_service.remove_token()
            logger.info("Token removed from cache service.")
        else:
            logger.error("Cache service is not initialized.")
            print("Cache service is not initialized.")

    def deduplicate_loads(self, loadsParam):
        db_loads = self.__fetch_db_loads()
        if db_loads is None or len(db_loads) == 0:
            logger.error("Failed to fetch existing loads from the database.")
            print("Failed to fetch existing loads from the database or it is empty.")
            return []

        deduplicated_loads = self.__array_deduplicator.apply_deduplication(target=loadsParam, 
                                                                           based_on=db_loads, 
                                                                           target_id_keyword='id', 
                                                                           base_id_keyword='external_load_id', 
                                                                           attributes_compare_callback=self.__attributes_compare_callback)
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
    
    def clear_cache(self):
        if self.__cache_service is not None:
            self.__cache_service.clear_all()
            logger.info("Cache cleared successfully.")
        else:
            logger.error("Cache service is not initialized.")
            print("Cache service is not initialized.")

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
        # Extract broker name from shipper info if available
        brokerage = load.get('shipper', {}).get(
            'companyName', 'Central Dispatch')
        # Calculate total weight from vehicles
        total_weight = 0
        for vehicle in load.get('vehicles', []):
            if vehicle and vehicle.get('shippingSpecs') and vehicle.get('shippingSpecs').get('weight'):
                total_weight += vehicle.get('shippingSpecs').get('weight', 0)

        load_model_instance = LoadModel(
            external_load_id=str(load.get('id', '')),
            brokerage=brokerage,
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
            logger.info(
                "No new loads to process, every load is already in the database")
            print("No new loads to process, every load is already in the database")
            return

        if len(non_duplicate_loads) > 0:
            load_model_instances = [
                model for model in (self.__format_and_get_load_model(load) for load in non_duplicate_loads)
                if model is not None  # Filter out None values that result from KeyError
            ]

            # Only proceed if there are valid models to save
            if load_model_instances and self.__db_Session is not None:
                self.__db_Session.bulk_save_objects(load_model_instances)
                self.__db_Session.commit()
                time.sleep(self.__in_between_delay)
                logger.info(
                    f"Inserted {len(load_model_instances)} loads into DB")
            else:
                logger.info("No valid loads to insert into DB")

    def fetch_loads(self, state):
        if self.__cache_service is not None and self.__api_client is not None:
            token = self.__cache_service.get_token()
            self.__api_client.set_authorization_header(token)
        
        try:
            loads_response = self.__api_client.post("https://bff.centraldispatch.com/listing-search/api/open-search",  # type: ignore
                                                    payload={
                                                        'vehicleCount': {
                                                            'min': 1,
                                                            'max': None,
                                                        },
                                                        'postedWithinHours': None,
                                                        'tagListingsPostedWithin': 2,
                                                        'trailerTypes': ['OPEN'],
                                                        'paymentTypes': [],
                                                        'vehicleTypes': [],
                                                        'operability': 'All',
                                                        'minimumPaymentTotal': None,
                                                        'readyToShipWithinDays': None,
                                                        'minimumPricePerMile': None,
                                                        'offset': 0,
                                                        'limit': 10000,
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
                                                        'locations': [{
                                                            'state': state,
                                                            'scope': 'Pickup',
                                                        },],
                                                    })
            response_json = loads_response.json()
            loads = response_json['items']
            if loads is None:
                logger.info("No loads found")
                print("Loads is None")
                raise ValueError("Loads is None")
            time.sleep(30)
            return loads
        except Exception as e:
            print(f"Error fetching loads: {e}")
            self.remove_token()
            

