from seleniumagent import SeleniumDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from gmail_verify import get_otp_from_gmail
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time
import random
from dotenv import load_dotenv
import os

load_dotenv()  
driver_path = os.getenv("CHROMEDRIVER")
trucksmarter = SeleniumDriver(driver_path=driver_path, headless=False)

trucksmarter.get_driver()
if trucksmarter.driver is not None:
    trucksmarter.driver.get("https://app.trucksmarter.com/login")
    email_input = trucksmarter.driver.find_element(By.NAME, "emailOrPhoneNumber")
    for char in "kaxamiqeladze@gmail.com":
        email_input.send_keys(char)
        time.sleep(0.1 + 0.2 * random.random())
    time.sleep(2)
    email_input.send_keys(Keys.RETURN)
    time.sleep(3)

try:
        # Wait for OTP input field container
        wait = WebDriverWait(trucksmarter.driver, 10) #type: ignore
        otp_container = wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "DallasForm_root__C7BnP"))
        )

        # Find and click first OTP input
        otp_inputs = trucksmarter.driver.find_elements(By.XPATH, "//input[contains(@class, 'DallasOneTimePasswordField_item__jNGy8')]") #type: ignore
        if not otp_inputs:
            raise Exception("OTP input fields not found")
        
        time.sleep(16)
        otp = get_otp_from_gmail()
        print("OTP received:", otp)
        time.sleep(2)
        
        otp_inputs[0].click()
        
        # Input OTP digits - focus moves automatically
        if isinstance(otp, str):
            for digit in otp:
                time.sleep(1)  # Small delay between digits
                active_element = trucksmarter.driver.switch_to.active_element #type: ignore
                active_element.send_keys(digit)
                time.sleep(1)  # Small delay between digits

        print("after submit click")
        time.sleep(3)
        # Locate the element using the provided XPath
        na_input = WebDriverWait(trucksmarter.driver, 30).until(
            EC.presence_of_element_located((By.XPATH, "//label[contains(@class, 'LoadBoardSearchForm_pickup__iipjF') and contains(@class, 'DallasFormField_root__L5LSI')]"))
        ) #type: ignore

        # Click the element
        na_input.click()

        # Write 'NA' into the element
        na_input.send_keys("N")
        time.sleep(0.5)
        na_input.send_keys("Y")
        time.sleep(2)
        # Press enter
        na_input.send_keys(Keys.RETURN)
        time.sleep(0.5)
        # Locate the trailer types dropdown button
        trailer_types_button = trucksmarter.driver.find_element(By.XPATH, "//button[@data-name='trailerTypes']") #type: ignore

        # Click the dropdown button to expand options
        trailer_types_button.click()
        time.sleep(0.5)

        # Locate and click the 'Hot Shot' option
        hot_shot_option = trucksmarter.driver.find_element(By.XPATH, "//span[contains(text(), 'Hot Shot')]") #type: ignore
        hot_shot_option.click()
        time.sleep(0.5)
        # Locate the search button using its class name
        search_button = trucksmarter.driver.find_element(By.XPATH, "//button[@type='submit']") #type: ignore

        # Click the search button
        search_button.click()
        
        print('Searched')
        time.sleep(100)
except TimeoutException:
    print("Timeout waiting for elements to load")

except Exception as e:
    print(f"Authentication error: {str(e)}")