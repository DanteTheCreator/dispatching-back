from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

class SeleniumDriver:
    def __init__(self, driver_path, headless=True):
        self.driver_path = driver_path
        self.headless = headless
        self.driver = None

    def initialize_driver(self):
        options = Options()
        options.binary_location = "/usr/bin/google-chrome"  # Path to Chromium

        # Set ChromeDriver path
        service = Service("/usr/local/bin/chromedriver")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--remote-debugging-port=9222")
        if self.headless:
            options.add_argument("--headless")
        self.driver = webdriver.Chrome(service=service, options=options)

    def get_driver(self):
        if self.driver is None:
            self.initialize_driver()
        return self.driver

    def quit_driver(self):
        if self.driver is not None:
            self.driver.quit()
            self.driver = None