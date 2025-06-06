from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from dotenv import load_dotenv
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
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        
        # Use local chromedriver
        if self.driver_path and os.path.exists(self.driver_path):
            service = Service(self.driver_path)
        else:
            # Try to find chromedriver.exe in central_agency folder
            central_driver = os.path.join(os.path.dirname(__file__), "central_agency", "chromedriver.exe")
            if os.path.exists(central_driver):
                service = Service(central_driver)
            else:
                raise FileNotFoundError("chromedriver.exe not found")
        
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
