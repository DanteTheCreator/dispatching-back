from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
import sys 
import os
import json
from datetime import datetime

from gmail_verify import get_otp_from_gmail
from selenuimagent import SeleniumDriver

def process_browser_logs_for_network_events(logs):
    """
    Return only logs which have a method that start with "Network."
    """
    for entry in logs:
        log = json.loads(entry["message"])["message"]
        if ("Network.response" in log["method"] or "Network.request" in log["method"]) and "params" in log:
            yield log

# Modify your SeleniumDriver class to enable CDP
truckerpath = SeleniumDriver(driver_path="C:/Users/tatog/OneDrive/სამუშაო დაფა/dispatching-back/chromedriver.exe", headless=True)
driver = truckerpath.get_driver()

request_data = {}

if driver is not None:
    # Enable network logging
    driver.execute_cdp_cmd('Network.enable', {})
    
    # Navigate to the page
    driver.get("https://loadboard.truckerpath.com/carrier/loads/loads-search")
    time.sleep(5)  # Wait for initial load

    # Get all requests during page load
    logs = driver.get_log('performance')

    # Track requests and responses
    for log in process_browser_logs_for_network_events(logs):
        try:
            if log["method"] == "Network.requestWillBeSent":
                request_data[log["params"]["requestId"]] = log["params"]["request"]
            elif log["method"] == "Network.responseReceived":
                request_id = log["params"]["requestId"]
                if request_id in request_data:
                    url = request_data[request_id]["url"]
                    if "truckloads-similar/shipment/user/exposure/similar/index/web" in url:
                        try:
                            response = driver.execute_cdp_cmd('Network.getResponseBody', {'requestId': request_id})
                            if response and 'body' in response:
                                response = json.loads(response['body'])
                                loads = response['data']['shipmentList']
                                print(len(loads))
                        except Exception as e:
                            print(f"Failed to get response body: {e}")
        except Exception as e:
            print(f"Error processing request: {e}")
            continue

    # Don't forget to disable network logging when done
    driver.execute_cdp_cmd('Network.disable', {})
    # email_input = truckerpath.driver.find_element(By.NAME, "emailOrPhoneNumber")
    # email_input.send_keys("laduka998877987@gmail.com")
    # email_input.send_keys(Keys.RETURN)
    # time.sleep(2)
    # otp = get_otp_from_gmail()
    # print(otp)
    # otp_inputs = truckerpath.driver.find_elements(By.CLASS_NAME, "DallasOneTimePasswordField_item__jNGy8")
    # if type(otp) == str and otp_inputs:
    #     for i, digit in enumerate(otp):
    #         otp_inputs[i].send_keys(digit)
    #     otp_inputs[-1].send_keys(Keys.RETURN)
    # else:
    #     print("OTP inputs not found or OTP is not a string")
    # try:
    #     search_button = trucksmarter.driver.find_element(By.XPATH, "//button[@type='submit' and contains(@class, 'DallasButton_rootCW77R')]")
    #     print(True)
    # except:
    #     print(False)
    