from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from dotenv import load_dotenv
from webdriver_manager.chrome import ChromeDriverManager
import os

load_dotenv()

CHROMEDRIVER = os.getenv("CHROMEDRIVER")
CHROME = os.getenv("CHROME")

class SeleniumDriver:
    def __init__(self, headless=False):
        self.driver_path = CHROMEDRIVER
        self.headless = headless
        self.driver = None

    def initialize_driver(self):
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        return self.driver

    def get_driver(self):
        if self.driver is None:
            self.initialize_driver()
        return self.driver

    def quit_driver(self):
        if self.driver is not None:
            self.driver.quit()
            self.driver = None