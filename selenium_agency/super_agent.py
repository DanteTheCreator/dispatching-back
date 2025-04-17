from selenium.webdriver.common.by import By
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_driver import SeleniumDriver
from dotenv import load_dotenv
import os
from gmail_verify import get_otp_from_gmail
import requests
import json
from api_client import APIClient
from super_cache import SuperCacheService
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from resources.models import LoadModel
from handlers import PeliasHandler

load_dotenv()

class SuperAgent:

    __selenium_driver = SeleniumDriver()
    __origin = "https://carrier.superdispatch.com"

    def __init__(self):
        self.__selenium_driver.initialize_driver()
        self.__driver = self.__selenium_driver.get_driver()
        # Your Gmail credentials
        self._email = os.getenv("EMAIL")
        self._password = os.getenv("PASSWORD_SUPER")
        self.__api_client = APIClient(base_url="https://api.loadboard.superdispatch.com", origin=self.__origin)
        self.__cache_service = SuperCacheService()
        self.__pelias_handler = PeliasHandler()

        self.__page = 0

    def __get_location_coordinates(self, location_str):
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

    def __format_and_get_load_model(self, load):
        # If the load comes wrapped in a container object, get the main load object
        load_data = load.get('load') if 'load' in load else load
        if not load_data:
            return None

        pickup_location = self.__format_pickup_location(load_data.get('pickup', {}))
        delivery_location = self.__format_delivery_location(load_data.get('delivery', {}))
        
        # Get coordinates for pickup and delivery
        pickup_coordinates = self.__get_location_coordinates(pickup_location)
        delivery_coordinates = self.__get_location_coordinates(delivery_location)
            
        load_model_instance = LoadModel(
            external_load_id=load_data.get('guid', ''),
            brokerage="Super Dispatch",
            pickup_location=f"{load_data.get('pickup', {}).get('venue', {}).get('city', '')}, {load_data.get('pickup', {}).get('venue', {}).get('state', '')} {load_data.get('pickup', {}).get('venue', {}).get('zip', '')}",
            delivery_location=f"{load_data.get('delivery', {}).get('venue', {}).get('city', '')}, {load_data.get('delivery', {}).get('venue', {}).get('state', '')} {load_data.get('delivery', {}).get('venue', {}).get('zip', '')}",
            pickup_points=pickup_coordinates,
            delivery_points=delivery_coordinates,
            price=str(load_data.get('price', '')),
            milage=float(load_data.get('distance_meters', 0)) / 1609.34,  # Convert meters to miles
            is_operational=not any(vehicle.get('is_inoperable', False) for vehicle in load_data.get('vehicles', [])),
            contact_phone=(load_data.get('shipper') or {}).get('contact_phone', ''),
            notes=load_data.get('instructions', ''),
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
            Price: ${load_model_instance.price}
            Milage: {round(load_model_instance.milage, 2)} miles
            Operational: {load_model_instance.is_operational}
            Contact: {load_model_instance.contact_phone}
            Created: {load_model_instance.created_at}
            """)
        return load_model_instance

    def __get_token(self):
        cookies = self.__driver.get_cookies()
        user_token = None
        for cookie in cookies:
            if cookie['name'] == 'userToken':
                user_token = cookie['value']
                break
        if user_token:
            print(f"User token found: {user_token}")
            self.__cache_service.set_token(user_token)
            return user_token
        else:
            print("User token not found in cookies")
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
            email_field.send_keys(self._email)
            time.sleep(in_between_delay)
            password_field.send_keys(self._password)
            time.sleep(in_between_delay)
            login_button.click()

            #waiting for the page to load and verification code to arrive
            time.sleep(10)

            otp = get_otp_from_gmail('Super Dispatch Verification Code')

            time.sleep(in_between_delay)

            otp_field = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[contains(@name, code)]")))
            time.sleep(in_between_delay)
            otp_field.send_keys(otp)
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
        print("loads count:", len(loads))
        load_count = 0
        for load in loads:
            load_count += 1
            print(f"saving load #{load_count}...")
            load_model_instance = self.__format_and_get_load_model(load)
            #load_model_instance.save()
            time.sleep(100)
            time.sleep(in_between_delay)
            print(f"load #{load_count} saved")
        time.sleep(in_between_delay)
        self.__page += 1

    def start_filling_db_cycle(self, in_between_delay=1):
        token = self.cache_service.get_token()
        loads_response = self.api_client.post("/internal/v3/loads/search", 
                            token=token, 
                            payload={},
                            params={"page": self.page, "size": 100})
        if loads_response.status_code == 401:
            self.cache_service.clear_all()
            return

        loads = loads_response.json()['data']
        logger.info(f"Loads count: {len(loads)}")
        existing_load_ids = {id_tuple[0] for id_tuple in self.db_Session.query(LoadModel.external_load_id).all()}
        # print(existing_load_ids)

        loads = [load for load in loads if load.get('load').get('guid') not in existing_load_ids]
        logger.info(f"New loads to process: {len(loads)}")
        print(loads)
        if len(loads) > 0:
            load_model_instances = [
                self.format_and_get_load_model(load) for load in loads
            ]
        # Bulk insert
            self.db_Session.bulk_save_objects(load_model_instances)
            self.db_Session.commit()
            time.sleep(in_between_delay)
            logger.info("Loads inserted into DB")
        self.page += 1

    def run(self):
        while True:
            if self.__cache_service.token_exists() == False:
                self.__start_login_cycle(in_between_delay=1)
            else:
                self.__start_filling_db_cycle(in_between_delay=2)


agent = SuperAgent()
agent.run()
