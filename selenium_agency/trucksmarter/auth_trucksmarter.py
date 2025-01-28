
from selenium_agency.selenuimagent import SeleniumDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
from .trucksmarter_api_service import TrucksmarterServiceApi
from dotenv import load_dotenv
import os


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
    
        param_string = self.__get_query_param_str()
        otp = self.__email_verifier.get_otp()
        print("otp received", otp)

        if self.__trucksmarter.driver is not None:
            self.__trucksmarter.driver.get(f"https://app.trucksmarter.com/verify/email{param_string}")
            time.sleep(3)
            otp_main_input = self.__trucksmarter.driver.find_element(By.CLASS_NAME, "DallasForm_root__C7BnP")
            otp_first_input = self.__trucksmarter.driver.find_element(By.CLASS_NAME, "DallasOneTimePasswordField_item__jNGy8")
            time.sleep(1)
            otp_first_input.click()
            time.sleep(1)
            #otp_input = self.__trucksmarter.driver.switch_to.active_element
            print("otp input: ", otp_main_input)

            if type(otp) == str:
                print("SENDING KEYS")
                otp_main_input.send_keys(otp)
            time.sleep(5)
            try:
                search_button = self.__trucksmarter.driver.find_element(By.XPATH, "//button[@type='submit' and contains(@class, 'DallasButton_rootCW77R')]")
                print(True)
            except:
                print(False)

    