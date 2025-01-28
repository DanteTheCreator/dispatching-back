from selenium_agency.selenuimagent import SeleniumDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
from .trucksmarter_api_service import TrucksmarterServiceApi
from .trucksmarter_app_service import TrucksmarterServiceApp
from dotenv import load_dotenv
import os
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


from selenium_agency.otp_verifiers.gmail_verifiers.trucksmarter_verifier import TruckSmarterVerifier

class AuthTrucksmarter:

    def __init__(self):
        self.__configure_credentials()
        self.__configure_services()
        self.__configure_selenium()

    # PRIVATE CONFIGURATION METHODS
    def __configure_credentials(self):
        load_dotenv()
        self.__email = os.getenv("EMAIL")
        self.__password = os.getenv("PASSWORD")

    def __configure_services(self):
        self.__service_api = TrucksmarterServiceApi()
        self.__service_app = TrucksmarterServiceApp()
        self.__email_verifier = TruckSmarterVerifier(email=self.__email, password=self.__password)

    def __configure_selenium(self):
        self.__trucksmarter = SeleniumDriver(driver_path="/Users/workingkakha/Desktop/chromedriver-mac-arm64/chromedriver", headless=False)
        self.__trucksmarter.get_driver()

    # PRIVATE METHODS
    def __get_vendor_method_id(self):
        vendor_method_id_response = self.__service_api.post("/auth/otp/email/start", 
                                                        data={"email": self.__email}, 
                                                        headers={"User-Agent": "PostmanRuntime/7.43.0"})
        print("vendor_method_id_response", vendor_method_id_response)
        vendor_method_id = vendor_method_id_response["vendorMethodId"]
        return vendor_method_id
    
    def __get_query_param_str(self):

        def build_query_string(params):
            return '?' + '&'.join([f"{param['key']}={param['value']}" for param in params])
        
        vendor_method_id = self.__get_vendor_method_id()
        params = [
            {'key': 'address', 'value': self.__email},
            {'key': 'vendorMethodId', 'value': vendor_method_id},
            {'key': 'authAction', 'value': 'Login'},
            {'key': '_rsc', 'value': 'crp2t'}
        ]
        param_query_string = build_query_string(params)
        return param_query_string
    
    # PUBLIC METHODS

    def authenticate(self):
        try:
            param_string = self.__get_query_param_str()

            if self.__trucksmarter.driver is not None:
                self.__trucksmarter.driver.get(f"https://app.trucksmarter.com/verify/email{param_string}")
                
                # Wait for OTP input field container
                wait = WebDriverWait(self.__trucksmarter.driver, 10)
                otp_container = wait.until(
                    EC.presence_of_element_located((By.CLASS_NAME, "DallasForm_root__C7BnP"))
                )

                # Find and click first OTP input
                otp_inputs = self.__trucksmarter.driver.find_elements(By.XPATH, "//input[contains(@class, 'DallasOneTimePasswordField_item__jNGy8')]")
                if not otp_inputs:
                    raise Exception("OTP input fields not found")
                
                time.sleep(10)
                otp = self.__email_verifier.get_otp()
                print("OTP received:", otp)
                time.sleep(2)
                
                otp_inputs[0].click()
                
                # Input OTP digits - focus moves automatically
                if isinstance(otp, str):
                    for digit in otp:
                        time.sleep(1)  # Small delay between digits
                        active_element = self.__trucksmarter.driver.switch_to.active_element
                        active_element.send_keys(digit)
                        time.sleep(1)  # Small delay between digits

                # Wait for submit button
                submit_button = wait.until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//button[@type='submit' and contains(@class, 'DallasButton_rootCW77R')]")
                    )
                )
                print("before submit click")
                submit_button.click()
                print("after submit click")
                
                return True

        except TimeoutException:
            print("Timeout waiting for elements to load")
            return False
        except Exception as e:
            print(f"Authentication error: {str(e)}")
            return False