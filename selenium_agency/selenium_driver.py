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
            # Get chromedriver path from environment variable or use default system path
            chromedriver_path = os.getenv('CHROMEDRIVER', '/usr/local/bin/chromedriver')
            
            if os.path.exists(chromedriver_path):
                service = Service(chromedriver_path)
            else:
                raise FileNotFoundError(f"chromedriver not found at {chromedriver_path}")
        
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
