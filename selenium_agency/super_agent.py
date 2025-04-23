from selenium.webdriver.common.by import By
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_driver import SeleniumDriver
from dotenv import load_dotenv
from selenium_agency.otp_verifiers.gmail_verify import get_otp_from_gmail_super
from selenium_agency.api.api_client import APIClient
from selenium_agency.api.super_api_client import SuperAPIClient
from selenium_agency.cache.super_cache import SuperCacheService
from resources.models import LoadModel, get_db
import logging
from geoalchemy2.elements import WKTElement
from selenium_agency.api.handlers import GraphhopperHandler, BulkRequestHandler

load_dotenv()

script_dir = os.path.dirname(os.path.abspath(__file__))

# Create the full path to the log file
log_file_path = os.path.join(script_dir, 'logs', 'super_agent.log')

# Configure logging
logging.basicConfig(
   filename=log_file_path,
   level=logging.INFO,
   format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class SuperAgent:

    __selenium_driver = SeleniumDriver()

    def __init__(self):
        self.__selenium_driver.initialize_driver()
        self.__driver = self.__selenium_driver.get_driver()
        # Your Gmail credentials
        self._email = os.getenv("EMAIL_SUPER")
        self._password = os.getenv("PASSWORD_SUPER")
        self.__api_client = SuperAPIClient()
        self.__cache_service = SuperCacheService()
        self.__db_Session =  next(get_db())
        self.__page = 0
        self.__bulk_request_handler = BulkRequestHandler()

    def __format_and_get_load_model(self, load):
        # If the load comes wrapped in a container object, get the main load object
        load_data = load.get('load') if 'load' in load else load
        if not load_data:
            return None

        instructions = load_data.get('instructions', '')
            
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
            created_at=load_data.get('created_at', '')
        )

        print(f"""
            Load Details:
            ------------
            External ID: {load_model_instance.external_load_id}
            Brokerage: {load_model_instance.brokerage}
            Pickup: {load_model_instance.pickup_location}
            Delivery: {load_model_instance.delivery_location}
            Pickup Coordinates: {load_model_instance.pickup_points}
            Delivery Coordinates: {load_model_instance.delivery_points}
            Price: ${load_model_instance.price}
            Milage: {round(load_model_instance.milage, 2)} miles
            Operational: {load_model_instance.is_operational}
            Contact: {load_model_instance.contact_phone}
            Created: {load_model_instance.created_at}
            """)
        return load_model_instance

    def __format_pickup_location(self, pickup_data):
        if not pickup_data or not pickup_data.get('venue'):
            return ''
        venue = pickup_data['venue']
        address_part = f"{venue.get('metro_area', '')}, " if venue.get('metro_area') else ""
        return f"{address_part}{venue.get('city', '')}, {venue.get('state', '')} {venue.get('zip', '')}"

    def __format_delivery_location(self, delivery_data):
        if not delivery_data or not delivery_data.get('venue'):
            return ''
        venue = delivery_data['venue']
        address_part = f"{venue.get('metro_area', '')}, " if venue.get('metro_area') else ""
        return f"{address_part}{venue.get('city', '')}, {venue.get('state', '')} {venue.get('zip', '')}"

    def __batch_save_loads(self, loads, in_between_delay=1):
        if len(loads) > 0:
            bulk_locations = []
            for load in loads:
                pickup_location = self.__format_pickup_location(load.get('load').get('pickup', {}))
                delivery_location = self.__format_delivery_location(load.get('load').get('delivery', {}))
                load['pickup_location'] = pickup_location
                load['delivery_location'] = delivery_location
                bulk_locations.append({"pickup_location": pickup_location, "delivery_location": delivery_location})

            bulk_coordinates = self.__bulk_request_handler.post("/bulk_geocode", payload=bulk_locations).json()

            print("received bulk coordinates: ", bulk_coordinates)
            for index, bulk_coordinate in enumerate(bulk_coordinates):
                pickup_location_coordinate = bulk_coordinate.get('pickup_coordinates')
                delivery_location_coordinate = bulk_coordinate.get('delivery_coordinates')
                pickup_points = WKTElement(f'POINT({pickup_location_coordinate[0]} {pickup_location_coordinate[1]})') if pickup_location_coordinate else None
                delivery_points = WKTElement(f'POINT({delivery_location_coordinate[0]} {delivery_location_coordinate[1]})') if delivery_location_coordinate else None
                loads[index]['pickup_points'] = pickup_points
                loads[index]['delivery_points'] = delivery_points
                
            load_model_instances = [
                self.__format_and_get_load_model(load) for load in loads
            ]
            # Bulk insert
            self.__db_Session.bulk_save_objects(load_model_instances)
            self.__db_Session.commit()
            time.sleep(in_between_delay)
            logger.info("Loads inserted into DB")

    def __get_token(self):
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
            self.__cache_service.set_token(user_token)
            return user_token
        else:
            logger.info("User token not found in cookies")
            self.__needs_authorizaton = True
            return None
            
    def __start_login_cycle(self, in_between_delay=1):
        if self.__driver is not None:
            self.__driver.get("https://carrier.superdispatch.com/tms/login/")
             # Wait for page to load
            wait = WebDriverWait(self.__driver, 10)
            time.sleep(in_between_delay)
            email_field = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[contains(@class, 'MuiInputBase-input MuiOutlinedInput-input')]")))
            password_field = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[contains(@class, 'MuiInputBase-input MuiOutlinedInput-input MuiInputBase-inputAdornedEnd MuiOutlinedInput-inputAdornedEnd')]")))
            login_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'Button__ButtonRoot-SD__sc-1pwdpe3-0 bjrslb')]")))
            time.sleep(in_between_delay)
            email_field.send_keys(self._email or '')
            time.sleep(in_between_delay)
            password_field.send_keys(self._password or '')
            time.sleep(in_between_delay)
            login_button.click()

            #waiting for the page to load and verification code to arrive
            time.sleep(10)

            otp = get_otp_from_gmail_super('Super Dispatch Verification Code')

            time.sleep(in_between_delay)

            otp_field = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[contains(@name, code)]")))
            time.sleep(in_between_delay)
            otp_field.send_keys(otp or '')
            time.sleep(in_between_delay * 2)
            button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'Button__ButtonRoot-SD__sc-1pwdpe3-0 bjrslb')]")))
            time.sleep(in_between_delay)
            button.click()
            time.sleep(5)

            loadboard_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, '/loadboard')]")))
            time.sleep(in_between_delay)
            time.sleep(10)
            loadboard_button.click()
            time.sleep(5)

            self.__get_token()

    def __start_filling_db_cycle(self, in_between_delay=1):
        print("start filling db cycle")
        token = self.__cache_service.get_token()
        self.__api_client.set_authorization_header(token)
        loads_response = self.__api_client.post("/internal/v3/loads/search", 
                            token=token, 
                            payload={},
                            params={"page": self.__page, "size": 100})
        if loads_response.status_code == 401:
            self.__cache_service.clear_all()
            return
        
        loads = loads_response.json()['data']
        logger.info(f"Loads count: {len(loads)}")
        
        # First filter out loads already in the database
        existing_load_ids = {id_tuple[0] for id_tuple in self.__db_Session.query(LoadModel.external_load_id).all()}
        loads = [load for load in loads if load.get('load').get('guid') not in existing_load_ids]
        
        # Then filter out duplicates based on price, mileage, pickup and delivery locations
        unique_loads = {}
        for load in loads:
            # Create a key from the attributes we want to check for duplicates
            pickup_venue = load.get('load', {}).get('pickup', {}).get('venue', {})
            delivery_venue = load.get('load', {}).get('delivery', {}).get('venue', {})
            
            pickup_location = f"{pickup_venue.get('city', '')}, {pickup_venue.get('state', '')} {pickup_venue.get('zip', '')}"
            delivery_location = f"{delivery_venue.get('city', '')}, {delivery_venue.get('state', '')} {delivery_venue.get('zip', '')}"
            
            key = (
                load.get('load', {}).get('price', 0),
                load.get('load', {}).get('distance_meters', 0),
                pickup_location,
                delivery_location
            )
            
            # Only add the load if we haven't seen this combination before
            if key not in unique_loads:
                unique_loads[key] = load
        
        # Convert back to a list
        loads = list(unique_loads.values())
        
        logger.info(f"New loads to process after deduplication: {len(loads)}")
        
        self.__batch_save_loads(loads, in_between_delay=in_between_delay)

        self.__page += 1

    def run(self):
        while True:
            if self.__cache_service.token_exists() == False:
                self.__start_login_cycle(in_between_delay=1)
            else:
                self.__start_filling_db_cycle(in_between_delay=2)


agent = SuperAgent()
agent.run()
