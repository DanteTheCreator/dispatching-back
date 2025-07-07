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
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-software-rasterizer")
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")
        chrome_options.add_argument("--disable-renderer-backgrounding")
        chrome_options.add_argument("--disable-features=TranslateUI,VizDisplayCompositor")
        chrome_options.add_argument("--disable-ipc-flooding-protection")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-images")
        chrome_options.add_argument("--memory-pressure-off")
        chrome_options.add_argument("--max_old_space_size=4096")
        chrome_options.add_argument("--remote-debugging-port=9222")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Use local chromedriver
        if self.driver_path and os.path.exists(self.driver_path):
            service = Service(self.driver_path)
            print(f"🔧 Using chromedriver from: {self.driver_path}")
        else:
            # Get chromedriver path from environment variable or use default system path
            chromedriver_path = os.getenv('CHROMEDRIVER', '/usr/local/bin/chromedriver')
            
            if os.path.exists(chromedriver_path):
                service = Service(chromedriver_path)
                print(f"🔧 Using chromedriver from: {chromedriver_path}")
            elif os.path.exists('/usr/local/bin/chromedriver'):
                service = Service('/usr/local/bin/chromedriver')
                print("🔧 Using chromedriver from: /usr/local/bin/chromedriver")
            else:
                print("❌ Chromedriver not found in expected locations")
                print("🔍 Available files in /usr/local/bin/:")
                try:
                    import subprocess
                    result = subprocess.run(['ls', '-la', '/usr/local/bin/'], capture_output=True, text=True)
                    print(result.stdout)
                except:
                    pass
                raise FileNotFoundError(f"chromedriver not found at {chromedriver_path}")
        
        print("🚀 Initializing Chrome WebDriver...")
        try:
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            print("✅ Chrome WebDriver initialized successfully!")
        except Exception as e:
            print(f"❌ Failed to initialize Chrome WebDriver: {e}")
            raise e
        return self.driver

    def get_driver(self):
        if self.driver is None:
            self.initialize_driver()
        return self.driver

    def quit_driver(self):
        if self.driver is not None:
            self.driver.quit()
            self.driver = None
