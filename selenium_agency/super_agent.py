from selenium.webdriver.common.by import By
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_driver import SeleniumDriver
from dotenv import load_dotenv
import os
from gmail_verify import get_otp_from_gmail
from api_client import APIClient
from super_cache import SuperCacheService
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from resources.models import LoadModel, get_db
import logging
import os
from handlers import PeliasHandler
from geoalchemy2.elements import WKTElement
from handlers import GraphhopperHandler, BulkRequestHandler

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
    __origin = "https://carrier.superdispatch.com"

    def __init__(self):
        self.__selenium_driver.initialize_driver()
        self.__driver = self.__selenium_driver.get_driver()
        # Your Gmail credentials
        self._email = os.getenv("SUPEREMAIL")
        self._password = os.getenv("PASSWORD_SUPER")
        self.__api_client = APIClient(base_url="https://api.loadboard.superdispatch.com", origin=self.__origin)
        self.__cache_service = SuperCacheService()
        self.__db_Session =  next(get_db())
        self.__page = 0
        self.__pelias_handler = PeliasHandler()
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

    def __get_location_coordinates(self, location_str):
        time.sleep(0.5)
        response = self.__pelias_handler.get(url="/v1/search", params={"text": location_str})
        if response.status_code == 200:
            data = response.json()
            if data.get('features') and len(data['features']) > 0:
                coordinates = data['features'][0]['geometry']['coordinates']
                return coordinates
        return None
    
    def __format_pickup_location(self, pickup_data):
        if not pickup_data or not pickup_data.get('venue'):
            return ''
        venue = pickup_data['venue']
        return f"{venue.get('city', '')}, {venue.get('state', '')} {venue.get('zip', '')}"

    def __format_delivery_location(self, delivery_data):
        if not delivery_data or not delivery_data.get('venue'):
            return ''
        venue = delivery_data['venue']
        return f"{venue.get('city', '')}, {venue.get('state', '')} {venue.get('zip', '')}"

    def __batch_save_loads(self, loads, in_between_delay=1):
        if len(loads) > 0:
            bulk_locations = []
            for load in loads:
                pickup_location = self.__format_pickup_location(load.get('pickup', {}))
                delivery_location = self.__format_delivery_location(load.get('delivery', {}))
                load['pickup_location'] = pickup_location
                load['delivery_location'] = delivery_location
                bulk_locations.append({"pickup_location": pickup_location, "delivery_location": delivery_location})
            
            time.sleep(5)
            print("sending bulk locations: ", bulk_locations)
            time.sleep(5)

            bulk_coordinates = self.__bulk_request_handler.post("/bulk_geocode", payload=bulk_locations)

            time.sleep(5)
            print("received bulk coordinates: ", bulk_coordinates)
            time.sleep(5)

            time.sleep(0.5)
            for index, bulk_coordinate in enumerate(bulk_coordinates):
                pickup_location_coordinate = bulk_coordinate.get('pickup_location')
                delivery_location_coordinate = bulk_coordinate.get('delivery_location')
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

            otp = get_otp_from_gmail('Super Dispatch Verification Code')

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
            loadboard_button.click()
            time.sleep(5)

            self.__get_token()

    def __start_filling_db_cycle(self, in_between_delay=1):
        token = self.__cache_service.get_token()
        loads_response = self.__api_client.post("/internal/v3/loads/search", 
                            token=token, 
                            payload={},
                            params={"page": self.__page, "size": 100})
        if loads_response.status_code == 401:
            self.__cache_service.clear_all()
            return
        
        loads = loads_response.json()['data']
        logger.info(f"Loads count: {len(loads)}")
        existing_load_ids = {id_tuple[0] for id_tuple in self.__db_Session.query(LoadModel.external_load_id).all()}
        # print(existing_load_ids)

        loads = [load for load in loads if load.get('load').get('guid') not in existing_load_ids]
        logger.info(f"New loads to process: {len(loads)}")
        
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
