import sys
import os
# Append the project root directory to sys.path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)
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
from central_interactor import CentralInteractor

load_dotenv()

script_dir = os.path.dirname(os.path.abspath(__file__))

# Create the full path to the log file
log_file_path = os.path.join(script_dir, 'logs', 'central_agent.log')

# Configure logging
logging.basicConfig(
    filename=log_file_path,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class CentralAgent:

    __selenium_driver = SeleniumDriver()
    __origin = ""
    __in_between_delay = 15

    def __init__(self):
        self.__selenium_driver.initialize_driver()
        self.__driver = self.__selenium_driver.get_driver()
        # Your Gmail credentials
        self._email = os.getenv("CENTRAL_USER")
        self._password = os.getenv("CENTRAL_PASSWORD")
        #self.__api_client = APIClient(url='', origin=self.__origin)
        self.__api_client = CentralAPIClient()
        self.__cache_service = CentralCacheService()
        self.__db_Session = next(get_db())
        self.__central_interactor = CentralInteractor(self.__selenium_driver, self.__api_client, self.__cache_service, self.__db_Session)
        self.__state_index = 0
        self.states = [
            'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'DC', 'FL',
            'GA', 'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME',
            'MD', 'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH',
            'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI',
            'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI',
            'WY']
        
    def __load_page(self):
        self.__driver.get("https://id.centraldispatch.com/Account/Login?ReturnUrl=%2Fconnect%2Fauthorize%2Fcallback%3Fclient_id%3Dcentraldispatch_authentication%26scope%3Dlisting_service%2520offline_access%2520openid%26response_type%3Dcode%26redirect_uri%3Dhttps%253A%252F%252Fsite.centraldispatch.com%252Fprotected") # type: ignore
        # Wait for page to load
        self.__wait = WebDriverWait(self.__driver, 10) # type: ignore
        time.sleep(self.__in_between_delay)
        time.sleep(5)

    def __authorize(self):
        # Use the correct ID selectors from the HTML
        email_field = self.__wait.until(
            EC.element_to_be_clickable((By.ID, "Username")))
        password_field = self.__wait.until(
            EC.element_to_be_clickable((By.ID, "password")))
        login_button = self.__wait.until(
            EC.element_to_be_clickable((By.ID, "loginButton")))

        time.sleep(self.__in_between_delay)
        email_field.send_keys(self._email or '')
        time.sleep(self.__in_between_delay)
        password_field.send_keys(self._password or '')
        time.sleep(self.__in_between_delay)
        login_button.click()

        # Wait for login to complete
        time.sleep(1)

    def __verify(self):
        send_code_button = self.__wait.until(
        EC.element_to_be_clickable((By.ID, "sendCodeButton")))
        send_code_button.click()
        time.sleep(5)
        otp = get_otp_from_gmail_central('Central Dispatch')
        otp_field = self.__wait.until(
        EC.element_to_be_clickable((By.ID, "VerificationCode")))
        time.sleep(self.__in_between_delay)
        otp_field.send_keys(otp or '')
        time.sleep(self.__in_between_delay-10)
        button = self.__wait.until(
        EC.element_to_be_clickable((By.ID, "submitButton")))
        button.click()
        time.sleep(15)

    def __start_login_cycle(self):
        if self.__driver is not None:
            print("loading page...")
            self.__load_page()
            print("authorizing...")
            self.__authorize()
            print("verifying...")
            self.__verify()
            print("setting token...")
            self.__central_interactor.set_token()

    def __start_filling_db_cycle(self, state):
        loads = self.__central_interactor.fetch_loads(state)
        if loads is None:
            return None  # Propagate None if fetching failed
        non_duplicate_loads = self.__central_interactor.deduplicate_loads(loads)
        self.__central_interactor.save_loads_to_db(non_duplicate_loads)
        return loads # Return loads so run method can check status

    def run(self):
        while True:
            if self.__cache_service.token_exists():
                loads = self.__start_filling_db_cycle(self.states[self.__state_index])
                if loads is None: # If fetching loads failed (e.g. token expired)
                    print("Failed to fetch loads, attempting to re-login.")
                    self.__cache_service.clear_all() # Clear potentially invalid token
                    # No need to call __start_login_cycle() here, it will be handled by the else block
                else:
                    self.__state_index += 1
                    if self.__state_index >= len(self.states):
                        self.__state_index = 0
                    time.sleep(30)
            else:
                try:
                    print("starting login cycle...")
                    self.__start_login_cycle()
                except Exception as e:
                    print(f"Error during login cycle: {e}") # Use f-string for better formatting
                    time.sleep(120) # Increased sleep time after login failure
                    continue


agent = CentralAgent()
agent.run()
