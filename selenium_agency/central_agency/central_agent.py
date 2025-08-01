import sys
import os
# Append the project root directory to sys.path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=== Central Agent Starting ===")
print(f"Python version: {sys.version}")
print(f"Current working directory: {os.getcwd()}")
print(f"Python path: {sys.path}")

import logging
from selenium.webdriver.common.by import By
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv
from selenium_agency.otp_verifiers.gmail_verify import get_otp_from_gmail_central
from selenium_agency.otp_verifiers.ringcentral_sms_extract import get_recent_central_dispatch_code
from central_configurator import CentralConfigurator

# Load .env file from the selenium_agency directory
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))


class CentralAgent:

    __in_between_delay = 12

    def __init__(self, driver=None):
        # Your Gmail credentials
        self._email = os.getenv("CENTRAL_USER")
        self._password = os.getenv("CENTRAL_PASSWORD")
        
        # Debug: Print environment status
        print(f"Environment variables loaded:")
        print(f"  CENTRAL_USER: {'✅ Set' if self._email else '❌ Not set'}")
        print(f"  CENTRAL_PASSWORD: {'✅ Set' if self._password else '❌ Not set'}")
        
        if not self._email or not self._password:
            print("❌ Missing required environment variables! Please check your .env file.")
            return
            
        central_configurator = CentralConfigurator()
        self.__central_interactor = central_configurator.configured_central_interactor()
        self.__driver = central_configurator.get_driver()

        self.__state_index = 0
        self.states = [
            'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'DC', 'FL',
            'GA', 'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME',
            'MD', 'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH',
            'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI',
            'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI',
            'WY']
        
    def __load_page(self):
        print("loading page...")
        self.__driver.get("https://id.centraldispatch.com/Account/Login?ReturnUrl=%2Fconnect%2Fauthorize%2Fcallback%3Fclient_id%3Dcentraldispatch_authentication%26scope%3Dlisting_service%2520offline_access%2520openid%26response_type%3Dcode%26redirect_uri%3Dhttps%253A%252F%252Fsite.centraldispatch.com%252Fprotected") # type: ignore
        # Wait for page to load
        self.__wait = WebDriverWait(self.__driver, 10) # type: ignore
        time.sleep(self.__in_between_delay)
        time.sleep(5)

    def __authorize(self):
        print("authorizing...")
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
        print("verifying...")
        # Check if verification code field exists
        try:
            otp_field = self.__wait.until(
            EC.element_to_be_clickable((By.ID, "VerificationCode")))
            print("Verification field found, proceeding with OTP...")
            time.sleep(10)
            otp = get_recent_central_dispatch_code(1)
            print(f"OTP received: {otp}")
            time.sleep(self.__in_between_delay)
            otp_field.send_keys(otp or '')
            time.sleep(self.__in_between_delay-10)
            button = self.__wait.until(
            EC.element_to_be_clickable((By.ID, "submitButton")))
            button.click()
            time.sleep(5)
        except Exception as e:
            print(f"Verification field not found or error occurred: {e}")
            print("Skipping OTP verification step...")

        time.sleep(5)

    def __start_login_cycle(self):
        if self.__driver is not None:
            try:
                self.__load_page()
                self.__authorize()
                self.__verify()
                self.__central_interactor.set_token()
                print("✅ Login cycle completed successfully!")
            except Exception as e:
                print(f"❌ Error in login cycle step: {e}")
                # Take a screenshot for debugging if possible
                try:
                    self.__driver.save_screenshot("/tmp/error_screenshot.png")
                    print("🖼️ Screenshot saved to /tmp/error_screenshot.png")
                except:
                    print("❌ Could not save screenshot")
                raise e

    def __start_filling_db_cycle(self, state):
        loads = self.__central_interactor.fetch_loads(state)
        needs_relogin = loads is None
        if needs_relogin == True:        
            return needs_relogin
        non_duplicate_loads = self.__central_interactor.deduplicate_loads(loads, state)
        filtered_loads = self.__central_interactor.filter_loads(non_duplicate_loads)
        self.__central_interactor.save_loads_to_db(filtered_loads)
        return loads 

    def cleanup(self):
        """Clean up resources"""
        try:
            if hasattr(self, '_CentralAgent__driver') and self.__driver:
                print("🧹 Cleaning up WebDriver...")
                self.__driver.quit()
                self.__driver = None
        except Exception as e:
            print(f"⚠️ Error during cleanup: {e}")

    def run(self):
        # Check if credentials are available
        if not self._email or not self._password:
            print("❌ Cannot start agent without proper credentials!")
            print("Please ensure CENTRAL_USER and CENTRAL_PASSWORD are set in your .env file.")
            return
            
        print("🚀 Starting Central Agent...")
        print(f"📧 Using email: {self._email}")
        
        try:
            while True:
                if self.__central_interactor.token_exists():
                    try:
                        needs_relogin = self.__start_filling_db_cycle(self.states[self.__state_index])
                        if needs_relogin == True:
                            print("Token expired, relogin will start soon...")
                            continue
                        self.__state_index += 1
                        if self.__state_index >= len(self.states):
                            self.__state_index = 0
                        time.sleep(30)
                    except Exception as e:
                        print(f"Error during data processing cycle: {e}")
                        print("Continuing to next state after a short delay...")
                        self.__state_index += 1
                        if self.__state_index >= len(self.states):
                            self.__state_index = 0
                        time.sleep(60)  # Wait longer before retrying
                        continue
                else:
                    try:
                        print("starting login cycle...")
                        self.__start_login_cycle()
                    except Exception as e:
                        print(f"Error during login cycle: {e}") # Use f-string for better formatting
                        print("🔄 Cleaning up and retrying...")
                        self.cleanup()
                        # Reinitialize the driver for next attempt
                        try:
                            central_configurator = CentralConfigurator()
                            self.__central_interactor = central_configurator.configured_central_interactor()
                            self.__driver = central_configurator.get_driver()
                            print("🔄 Driver reinitialized successfully")
                        except Exception as reinit_error:
                            print(f"❌ Failed to reinitialize driver: {reinit_error}")
                        time.sleep(120) # Increased sleep time after login failure
                        continue
        except KeyboardInterrupt:
            print("Removing token...")
            print("keyboard interrupt exiting...")
            self.__central_interactor.remove_token()
            self.cleanup()
            quit()
        except Exception as e:
            print(f"❌ Unexpected error in main loop: {e}")
            self.cleanup()
            raise

agent = CentralAgent()
agent.run()
