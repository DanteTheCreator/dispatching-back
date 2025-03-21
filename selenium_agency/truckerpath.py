from selenium.webdriver.common.by import By
import time
import os
import json
from selenium_agency.selenium_driver import SeleniumDriver
from dotenv import load_dotenv
import os
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class TruckerpathAgent:

    __pick_ups = {
        "NY": "New York, NY, US"
    }

    def __init__(self):
        load_dotenv()
        CHROMEDRIVER = os.getenv("CHROMEDRIVER")
        self.__truckerpath = SeleniumDriver(driver_path=CHROMEDRIVER, headless=True)
        self.__driver = self.__truckerpath.get_driver()

    def __selenium_search_to_make_request(self, pick_up_state_abbr):
        if len(pick_up_state_abbr) != 2 and pick_up_state_abbr.upper() not in self.__pick_ups.keys:
            print("invalid state abbr")
            return 

        pick_up_value = self.__pick_ups[pick_up_state_abbr.upper()]

        if self.__driver is not None:
            # Enable network logging
            self.__driver.execute_cdp_cmd('Network.enable', {})
            
            # Navigate to the page
            self.__driver.get("https://loadboard.truckerpath.com/carrier/loads/loads-search")
            
            # Wait for page to load
            wait = WebDriverWait(self.__driver, 10)

            # Find and interact with pick-up location field
            pick_up = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(@class, 'tlant-select-selection-item')]")))
            pick_up.click()
            
            # Find the input field that appears after clicking
            input_field = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='search' and contains(@class, 'tlant-select-selection-search-input')]")))
            input_field.clear()
            input_field.send_keys(pick_up_value)
            time.sleep(4)
            
            # Wait for and select first suggestion
            time.sleep(2)  # Wait for suggestions to load
            suggestion = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'tlant-select-item-option-content')]")))
            suggestion.click()
            time.sleep(2)

            # Click search button
            search_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@type='submit' and contains(@class, '-module-searchButton-XywAX')]")))
            search_button.click()
            
            time.sleep(8)

    def fetchLoads(self, pick_up_state_abbr):
        self.__selenium_search_to_make_request(pick_up_state_abbr)
        try:
            logs = self.__driver.get_log('performance')
            for log in logs:
                # Parse the message string as JSON
                log_entry = json.loads(log['message'])
                
                # Navigate through the JSON structure
                if ('message' in log_entry and 
                    'params' in log_entry['message'] and
                    'response' in log_entry['message']['params'] and
                    'url' in log_entry['message']['params']['response']):
                    
                    url = log_entry['message']['params']['response']['url']
                    if url == 'https://api.truckerpath.com/tl/search/filter/web/v2':
                        request_id = log_entry['message']['params']['requestId']
                        try:
                            response = self.__driver.execute_cdp_cmd('Network.getResponseBody', {'requestId': request_id})
                            if response and 'body' in response:
                                response_data = json.loads(response['body'])
                                print("Response data:", response_data)
                        except Exception as e:
                            print(f"Failed to get response body: {e}")

        except KeyboardInterrupt:
            print("Monitoring stopped by user")
        except Exception as e:
            print(f"Main loop error: {e}")
            

agent = TruckerpathAgent()
agent.fetchLoads("NY")