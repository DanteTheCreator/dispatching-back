from selenium.webdriver.common.by import By
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_driver import SeleniumDriver

class CentralAgent:

    __selenium_driver = SeleniumDriver()

    def __init__(self):
        self.__selenium_driver.initialize_driver()
        self.__driver = self.__selenium_driver.get_driver()

    def login(self):
        if self.__driver is not None:
            self.__driver.get("https://id.centraldispatch.com/Account/Login")
            counter = 0
            while True:
                time.sleep(1)
                counter += 1
                print(f"count: {counter}")

agent = CentralAgent()
agent.login()
