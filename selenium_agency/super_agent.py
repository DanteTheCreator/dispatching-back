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

load_dotenv()

class SuperAgent:

    __selenium_driver = SeleniumDriver()
    __needs_authorizaton = True

    def __init__(self):
        self.__selenium_driver.initialize_driver()
        self.__driver = self.__selenium_driver.get_driver()
        # Your Gmail credentials
        self._email = os.getenv("EMAIL")
        self._password = os.getenv("PASSWORD_SUPER")

    def __login(self):
        if self.__driver is not None:
            self.__driver.get("https://carrier.superdispatch.com/tms/login/")
             # Wait for page to load
            wait = WebDriverWait(self.__driver, 10)
            time.sleep(1)
            email_field = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[contains(@class, 'MuiInputBase-input MuiOutlinedInput-input')]")))
            password_field = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[contains(@class, 'MuiInputBase-input MuiOutlinedInput-input MuiInputBase-inputAdornedEnd MuiOutlinedInput-inputAdornedEnd')]")))
            login_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'Button__ButtonRoot-SD__sc-1pwdpe3-0 bjrslb')]")))
            time.sleep(1)
            email_field.send_keys(self._email)
            time.sleep(1)
            password_field.send_keys(self._password)
            time.sleep(1)
            login_button.click()

            #waiting for the page to load and verification code to arrive
            time.sleep(10)

            otp = get_otp_from_gmail('Super Dispatch Verification Code')
            print(otp)

            time.sleep(1)

            otp_field = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[contains(@name, code)]")))
            time.sleep(1)
            otp_field.send_keys(otp)
            time.sleep(2)
            button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'Button__ButtonRoot-SD__sc-1pwdpe3-0 bjrslb')]")))
            time.sleep(1)
            button.click()
            time.sleep(5)

            token = self.__get_token()

            time.sleep(100)
            self.__needs_authorizaton = False

    def __get_token(self):
            cookies = self.__driver.get_cookies()
            user_token = None
            for cookie in cookies:
                if cookie['name'] == 'userToken':
                    user_token = cookie['value']
                    break
            if user_token:
                print(f"User token found: {user_token}")
                return user_token
            else:
                print("User token not found in cookies")
                return None

    def run(self):
        while self.__needs_authorizaton:
            self.__login()


agent = SuperAgent()
agent.run()
