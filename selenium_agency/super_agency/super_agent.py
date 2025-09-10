from selenium.webdriver.common.by import By
import sys
import os
# Add the project root directory to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(project_root)
# Keep the original append for backward compatibility
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_driver import SeleniumDriver
from dotenv import load_dotenv
from selenium_agency.otp_verifiers.gmail_verify import get_otp_from_gmail_super
from api_client import APIClient
from selenium_agency.api.super_api_client import SuperAPIClient
from selenium_agency.cache.super_cache import SuperCacheService
from resources.models import LoadModel, get_db
import logging
from geoalchemy2.elements import WKTElement
from api.handlers import GraphhopperHandler, BulkRequestHandler
from super_interactor import SuperInteractor

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
        # Don't create session here, create when needed
        self.__db_Session = None
        self.__bulk_request_handler = BulkRequestHandler()
        self.__super_interactor = SuperInteractor(
            self.__selenium_driver, 
            self.__api_client, 
            self.__cache_service, 
            self.__db_Session,
            self.__bulk_request_handler
        )
        self.__page = 0

    def _get_db_session(self):
        """Get a database session, creating one if needed"""
        if self.__db_Session is None:
            self.__db_Session = next(get_db())
        return self.__db_Session
    
    def _close_db_session(self):
        """Close the database session if it exists"""
        if self.__db_Session is not None:
            self.__db_Session.close()
            self.__db_Session = None

    def __start_login_cycle(self, in_between_delay=1):
        print("start login cycle")
        if self.__driver is not None:
            self.__driver.get("https://carrier.superdispatch.com/tms/login/")
             # Wait for page to load
            wait = WebDriverWait(self.__driver, 10)
            time.sleep(in_between_delay)
            print("email value", self._email)
            email_field = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[contains(@class, 'MuiInputBase-input MuiOutlinedInput-input')]")))
            email_field.send_keys(self._email or '')
            password_field = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[contains(@class, 'MuiInputBase-input MuiOutlinedInput-input MuiInputBase-inputAdornedEnd MuiOutlinedInput-inputAdornedEnd')]")))
            login_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'Button__ButtonRoot-SD__sc-1pwdpe3-0 bjrslb')]")))
            time.sleep(in_between_delay)
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

            loadboard_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'MuiBottomNavigationAction-root')]//span[text()='Loads']/..")))
            time.sleep(in_between_delay)
            loadboard_button.click()
            time.sleep(5)

            self.__super_interactor.get_token()

    def __start_filling_db_cycle(self, in_between_delay=1):
        print("start filling db cycle")
        loads = self.__super_interactor.fetch_loads(self.__page)
        if loads is None:
            return
        
        non_duplicate_loads = self.__super_interactor.deduplicate_loads(loads)
        
        if len(non_duplicate_loads) == 0:
            print("no new loads to process, every load is already in the database")
        else:
            self.__super_interactor.batch_save_loads(non_duplicate_loads, in_between_delay=in_between_delay)

        self.__page += 1

    def run(self):
        while True:
            if self.__cache_service.token_exists() == False:
                self.__start_login_cycle(in_between_delay=1)
            else:
                self.__start_filling_db_cycle(in_between_delay=2)
                time.sleep(30)


agent = SuperAgent()
agent.run()
