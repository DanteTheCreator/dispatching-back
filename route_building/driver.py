import sys
import os
# Add the parent directory to the Python path to find the resources module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from resources.models import DriverModel, get_db

class Driver:
    def __init__(self, driver_id):
        self.driver_id = driver_id
        self.db = None
        
        # Get driver info from database
        db = next(get_db())
        try:
            driver = db.query(DriverModel).filter(
                DriverModel.driver_id == self.driver_id).first()
            if not driver:
                raise ValueError(f"Driver with id {self.driver_id} not found")

            # Set attributes with value conversion
            self.full_name = driver.full_name
            self.location = driver.location
            self.trailer_size = driver.trailer_size
            try:
                self.desired_gross = float(getattr(driver, 'desired_gross', 0.0))
                self.max_milage = float(getattr(driver, 'max_milage', 0.0))
                self.desired_rpm = float(getattr(driver, 'desired_rpm', 0.0))
                self.active = driver.active
                self.phone = driver.phone
                self.states = driver.states if driver.states is not None else []
            except (ValueError, TypeError, AttributeError) as e:
                print(f"Error converting values: {e}")
        finally:
            db.close()
            self.desired_gross = 0.0
            self.desired_rpm = 0.0