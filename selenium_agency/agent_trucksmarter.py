import sys

sys.path.append('/root/dispatching_api')
sys.path.append('C:/Users/tatog/OneDrive/სამუშაო დაფა/dispatching-back')


from httpcore import TimeoutException
from seleniumagent import SeleniumDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
import os
import json
from random import random
from gmail_verify import get_otp_from_gmail
from dotenv import load_dotenv
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from resources.models import LoadModel

class TruckSmarterAgent():

    def __init__(self):
        load_dotenv()
        CHROMEDRIVER = os.getenv("CHROMEDRIVER")
        self.__trucksmarter = SeleniumDriver(driver_path=CHROMEDRIVER, headless=False)
        self.__driver = self.__trucksmarter.get_driver()

    def __login(self):
        if self.__driver is not None:
            self.__driver.get("https://app.trucksmarter.com/login")
            email_input = self.__driver.find_element(By.NAME, "emailOrPhoneNumber")
            for char in "kaxamiqeladze@gmail.com":
                email_input.send_keys(char)
                time.sleep(0.1 + 0.2 * random())
            time.sleep(2)
            email_input.send_keys(Keys.RETURN)
            time.sleep(3)

            try:
                wait = WebDriverWait(self.__driver, 10)
                otp_container = wait.until(
                    EC.presence_of_element_located((By.CLASS_NAME, "DallasForm_root__C7BnP"))
                )

                otp_inputs = self.__driver.find_elements(By.XPATH, "//input[contains(@class, 'DallasOneTimePasswordField_item__jNGy8')]")
                if not otp_inputs:
                    raise Exception("OTP input fields not found")
                
                time.sleep(12)
                otp = get_otp_from_gmail()
                print("OTP received:", otp)
                time.sleep(2)
                
                otp_inputs[0].click()
                
                if isinstance(otp, str):
                    for digit in otp:
                        time.sleep(1)
                        active_element = self.__driver.switch_to.active_element
                        active_element.send_keys(digit)
                        time.sleep(1)

                print("Logged In!")
                time.sleep(3)
                
            except TimeoutException:
                print("Timeout waiting for elements to load")
            except Exception as e:
                print(f"Authentication error: {str(e)}")
                
    def search_for_loads(self, state):
        if self.__driver is None:
            print("Driver not initialized")
            return
        
        if len(state) != 2:
            print("invalid state")
            return 
        
        try:
            na_input = WebDriverWait(self.__driver, 30).until(
            EC.presence_of_element_located((By.XPATH, "//label[contains(@class, 'LoadBoardSearchForm_pickup__iipjF') and contains(@class, 'DallasFormField_root__L5LSI')]"))
            )

            na_input.click()
            time.sleep(2)
            na_input.send_keys(state)
            time.sleep(2)
            na_input.send_keys(Keys.RETURN)
            time.sleep(0.5)
            trailer_types_button = self.__driver.find_element(By.XPATH, "//button[@data-name='trailerTypes']")

            trailer_types_button.click()
            time.sleep(0.5)

            hot_shot_option = self.__driver.find_element(By.XPATH, "//span[contains(text(), 'Hot Shot')]")
            hot_shot_option.click()
            time.sleep(0.5)
            search_button = self.__driver.find_element(By.XPATH, "//button[@type='submit']")

            search_button.click()
            time.sleep(5)
        except TimeoutException:
            print("Timeout waiting for elements to load")
        except Exception as e:
            print(f"Error during search for loads: {str(e)}") 

    def fetchLoads(self):
        
        try:    
            if self.__driver is not None:
                logs = self.__driver.get_log('performance') 
                for log in logs:
                    log_entry = json.loads(log['message'])
                    
                    if ('message' in log_entry and 
                        'params' in log_entry['message'] and
                        'response' in log_entry['message']['params'] and
                        'url' in log_entry['message']['params']['response']):
                        
                        url = log_entry['message']['params']['response']['url']
                        if url == 'https://api.trucksmarter.com/loads/searchV2Ungrouped':
                            request_id = log_entry['message']['params']['requestId']
                            try:
                                response = self.__driver.execute_cdp_cmd('Network.getResponseBody', {'requestId': request_id})
                                if response and 'body' in response:
                                    response_data = json.loads(response['body'])
                                    return response_data
                            except Exception as e:
                                print(f"Failed to get response body: {e}")

        except KeyboardInterrupt:
            print("Monitoring stopped by user")
        except Exception as e:
            print(f"Main loop error: {e}")
        
    def format_and_get_load_model(self, load):
        load_model_instance = LoadModel(
                    load_id=load.get('id'),
                    origin=load.get('pickup', {}).get('address', {}).get('city'),
                    destination=load.get('delivery', {}).get('address', {}).get('city'),
                    pickup_date=load.get('pickup', {}).get('appointmentStartTime'),
                    delivery_date=load.get('delivery', {}).get('appointmentStartTime'),
                    trailer_type=", ".join(load.get('equipment', {}).get('trailerTypes', [])),
                    weight=load.get('weight'),
                    rate=load.get('maxBidPriceCents'),
                    distance=load.get('distance')
                )
        return load_model_instance

    def run(self):
        is_logged_in = False
        states = ["CT", "DE", "GA", "ME", "MD", "MA", "NH", "NJ", "NY", "NC", "PA", "RI", "SC", "VT", "VA", "WV"]
        while True:
            self.__login()
            is_logged_in = True
            while is_logged_in:
                try:
                    for state in states:
                        self.search_for_loads(state) #search for loads in browser
                        loads = self.fetchLoads() #gets loads from response
                        for load in loads: #type: ignore
                            print(load)
                            print("#################")
                            time.sleep(5)
                            if load:
                                model_instance = self.format_and_get_load_model(load)
                                model_instance.save()
                except:
                    is_logged_in = False


if __name__ == "__main__":
    trucksmarter = TruckSmarterAgent()
    trucksmarter.run()