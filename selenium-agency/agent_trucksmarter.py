from selenuimagent import SeleniumDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from gmail_verify import get_otp_from_gmail
import time

trucksmarter = SeleniumDriver(driver_path="/usr/local/bin/chromedriver", headless=True)

trucksmarter.get_driver()
if trucksmarter.driver is not None:
    trucksmarter.driver.get("https://app.trucksmarter.com/login")
    email_input = trucksmarter.driver.find_element(By.NAME, "emailOrPhoneNumber")
    email_input.send_keys("laduka998877987@gmail.com")
    email_input.send_keys(Keys.RETURN)
    time.sleep(2)
    otp = get_otp_from_gmail()
    print(otp)
    otp_inputs = trucksmarter.driver.find_elements(By.CLASS_NAME, "DallasOneTimePasswordField_item__jNGy8")
    if type(otp) == str and otp_inputs:
        for i, digit in enumerate(otp):
            otp_inputs[i].send_keys(digit)
        otp_inputs[-1].send_keys(Keys.RETURN)
    else:
        print("OTP inputs not found or OTP is not a string")
    try:
        search_button = trucksmarter.driver.find_element(By.XPATH, "//button[@type='submit' and contains(@class, 'DallasButton_rootCW77R')]")
        print(True)
    except:
        print(False)
    