class Route:
    def __init__(self, driver):
        self.driver = driver
        self.loads = []
        self.load_ids = []
        self.milage = 50
        self.total_rpm = 0.0
        self.total_price = 0.0

    def add_load(self, load):
        # Add a load to the route
        self.loads.append(load)
        self.load_ids.append(load.load_id)
        self.milage += float(load.milage)
        self.total_price += float(load.price)
        try:
            if self.milage > 0:
                self.total_rpm = self.total_price / self.milage
            else:
                self.total_rpm = 0
                print("Zero mileage detected, setting RPM to zero")
        except Exception as e:
            print(f"Error calculating RPM: {str(e)}")
            self.total_rpm = 0