import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from geoalchemy2.elements import WKTElement
from handlers import PeliasHandler
import logging
from resources.models import LoadModel, get_db
from selenium.webdriver.common.by import By
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_driver import SeleniumDriver
from dotenv import load_dotenv
from gmail_verify import get_otp_from_gmail
from api_client import APIClient
from super_cache import SuperCacheService


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


class CentralAgent:

    __selenium_driver = SeleniumDriver()
    __origin = "https://carrier.superdispatch.com"

    def __init__(self):
        self.__selenium_driver.initialize_driver()
        self.__driver = self.__selenium_driver.get_driver()
        # Your Gmail credentials
        self._email = os.getenv("CENTRAL_USER")
        self._password = os.getenv("CENTRAL_PASSWORD")
        self.__api_client = APIClient(url='', origin=self.__origin)
        self.__cache_service = SuperCacheService()
        self.__db_Session = next(get_db())
        self.__page = 0
        self.__pelias_handler = PeliasHandler()

    def __format_and_get_load_model(self, load):
        if not load:
            return None

        pickup_location = f"{load['origin']['city']}, {load['origin']['state']} {load['origin']['zip']}"
        delivery_location = f"{load['destination']['city']}, {load['destination']['state']} {load['destination']['zip']}"

        pickup_coordinates = [load['origin']['geoCode']
                              ['longitude'], load['origin']['geoCode']['latitude']]
        delivery_coordinates = [load['destination']['geoCode']
                                ['longitude'], load['destination']['geoCode']['latitude']]

        # Convert coordinates to WKT format
        pickup_points = WKTElement(
            f'POINT({pickup_coordinates[0]} {pickup_coordinates[1]})') if pickup_coordinates else None
        delivery_points = WKTElement(
            f'POINT({delivery_coordinates[0]} {delivery_coordinates[1]})') if delivery_coordinates else None

        coordinates_note = f"Pickup coordinates: {pickup_coordinates}, Delivery coordinates: {delivery_coordinates}"
        instructions = load.get('additionalInfo', '')
        combined_notes = f"{instructions}\n{coordinates_note}"

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
            created_at=load.get('createdDate', '')
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
            self.__driver.get("https://id.centraldispatch.com/Account/Login?ReturnUrl=%2Fconnect%2Fauthorize%2Fcallback%3Fclient_id%3Dcentraldispatch_authentication%26scope%3Dlisting_service%2520offline_access%2520openid%26response_type%3Dcode%26redirect_uri%3Dhttps%253A%252F%252Fsite.centraldispatch.com%252Fprotected")
            # Wait for page to load
            wait = WebDriverWait(self.__driver, 10)
            time.sleep(in_between_delay)

            # Use the correct ID selectors from the HTML
            email_field = wait.until(
                EC.element_to_be_clickable((By.ID, "Username")))
            password_field = wait.until(
                EC.element_to_be_clickable((By.ID, "password")))
            login_button = wait.until(
                EC.element_to_be_clickable((By.ID, "loginButton")))

            time.sleep(in_between_delay)
            email_field.send_keys(self._email or '')
            time.sleep(in_between_delay)
            password_field.send_keys(self._password or '')
            time.sleep(in_between_delay)
            login_button.click()

            # Wait for login to complete
            time.sleep(1)
            send_code_button = wait.until(
                EC.element_to_be_clickable((By.ID, "sendCodeButton")))
            send_code_button.click()
            time.sleep(5)
            otp = get_otp_from_gmail('Central Dispatch')
            otp_field = wait.until(
                EC.element_to_be_clickable((By.ID, "VerificationCode")))
            time.sleep(in_between_delay)
            otp_field.send_keys(otp or '')
            time.sleep(in_between_delay)
            button = wait.until(
                EC.element_to_be_clickable((By.ID, "submitButton")))
            button.click()
            time.sleep(200)

            self.__get_token()

    def __start_filling_db_cycle(self, in_between_delay=1):
        token = self.__cache_service.get_token()
        loads_response = self.__api_client.post("https://bff.centraldispatch.com/listing-search/api/open-search",
                                                token=token,
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
                                                    'offset': 0,
                                                    'limit': 10,
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
        if loads_response.status_code == 401:
            self.__cache_service.clear_all()
            return

        loads = loads_response.json()['data']
        logger.info(f"Loads count: {len(loads)}")
        existing_load_ids = {id_tuple[0] for id_tuple in self.__db_Session.query(
            LoadModel.external_load_id).all()}
        # print(existing_load_ids)

        loads = [load for load in loads if load.get(
            'load').get('guid') not in existing_load_ids]
        logger.info(f"New loads to process: {len(loads)}")
        print(loads)
        if len(loads) > 0:
            load_model_instances = [
                self.__format_and_get_load_model(load) for load in loads
            ]
        # Bulk insert
            self.__db_Session.bulk_save_objects(load_model_instances)
            self.__db_Session.commit()
            time.sleep(in_between_delay)
            logger.info("Loads inserted into DB")
        self.__page += 1

    def run(self):
        while True:
            if self.__cache_service.token_exists() == False:
                self.__start_login_cycle(in_between_delay=1)
            else:
                self.__start_filling_db_cycle(in_between_delay=2)


agent = CentralAgent()
agent.run()
