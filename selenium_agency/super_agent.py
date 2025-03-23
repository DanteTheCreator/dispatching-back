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
            
    def __start_login_cycle(self, timer_count=1):
        if self.__driver is not None:
            self.__driver.get("https://carrier.superdispatch.com/tms/login/")
             # Wait for page to load
            wait = WebDriverWait(self.__driver, 10)
            time.sleep(timer_count)
            email_field = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[contains(@class, 'MuiInputBase-input MuiOutlinedInput-input')]")))
            password_field = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[contains(@class, 'MuiInputBase-input MuiOutlinedInput-input MuiInputBase-inputAdornedEnd MuiOutlinedInput-inputAdornedEnd')]")))
            login_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'Button__ButtonRoot-SD__sc-1pwdpe3-0 bjrslb')]")))
            time.sleep(timer_count)
            email_field.send_keys(self._email)
            time.sleep(timer_count)
            password_field.send_keys(self._password)
            time.sleep(timer_count)
            login_button.click()

            #waiting for the page to load and verification code to arrive
            time.sleep(10)

            otp = get_otp_from_gmail('Super Dispatch Verification Code')
            print(otp)

            time.sleep(timer_count)

            otp_field = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[contains(@name, code)]")))
            time.sleep(timer_count)
            otp_field.send_keys(otp)
            time.sleep(timer_count * 2)
            button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'Button__ButtonRoot-SD__sc-1pwdpe3-0 bjrslb')]")))
            time.sleep(timer_count)
            button.click()
            time.sleep(5)
            self.__get_token()

    def __start_filling_db_cycle(self, timer_count):
        loads_response = self.__api_client.get("/internal/v3/loads/search", token=token)
        if loads_response.status_code == 401:
            self.__cache_service.clear_all()
            return
        loads = loads_response.json()['data']
        print("loads count:", len(loads))
        load_count = 0
        for load in loads:
            load_count += 1
            print(f"saving load {load_count}")
            print(load)
            time.sleep(timer_count)
        time.sleep(timer_count)

    def run(self):
        while True:
            if self.__cache_service.token_exists() == False:
                self.__start_login_cycle(1)
            else:
                self.__start_filling_db_cycle(2)


agent = SuperAgent()
agent.run()
