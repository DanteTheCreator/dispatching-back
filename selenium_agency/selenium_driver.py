from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv
import os

load_dotenv()

# Your Gmail credentials
CHROMEDRIVER = os.getenv("CHROMEDRIVER")
CHROME = os.getenv("CHROME")

class SeleniumDriver:
    def __init__(self, headless=False):
        self.driver_path = CHROMEDRIVER
        self.headless = headless
        self.driver = None

    def initialize_driver(self):
        options = Options()
        options.binary_location = CHROME  # Path to Chromium

        # Set ChromeDriver path
        service = Service(ChromeDriverManager().install())
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        # Enable performance logging
        options.set_capability('goog:loggingPrefs', {
            'browser': 'ALL',
            'performance': 'ALL'
        })
        # options.add_argument("--headless")
        self.driver = webdriver.Chrome(service=service, options=options)

    def get_driver(self):
        if self.driver is None:
            self.initialize_driver()
        return self.driver

    def quit_driver(self):
        if self.driver is not None:
            self.driver.quit()
            self.driver = None