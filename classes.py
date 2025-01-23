from models import DriverModel, RouteModel, get_db, LoadModel
from sqlalchemy.orm import Session
from typing import List

class Driver:
    def __init__(self, driver_id):
        self.driver_id = driver_id
        self.db = next(get_db())
        
        # Get driver info from database
        driver = self.db.query(DriverModel).filter(DriverModel.driver_id == self.driver_id).first()
        if not driver:
            raise ValueError(f"Driver with id {self.driver_id} not found")
        
        # Set attributes with value conversion
        self.full_name = driver.full_name
        self.location = driver.location
        self.trailer_size = driver.trailer_size
        try:
            # Get the scalar value from Column objects if needed
            gross_value = getattr(driver.desired_gross, 'scalar_value', driver.desired_gross)
            rpm_value = getattr(driver.desired_rpm, 'scalar_value', driver.desired_rpm)
            
            self.desired_gross = float(gross_value)  # type: ignore
            self.desired_rpm = float(rpm_value) # type: ignore
        except (ValueError, TypeError, AttributeError) as e:
            print(f"Error converting values: {e}")
            self.desired_gross = 0.0
            self.desired_rpm = 0.0
        self.active = driver.active
        self.phone = driver.phone
        self.states = driver.states if driver.states is not None else []
        print(f"Driver attributes: driver_id={self.driver_id}, full_name={self.full_name}, location={self.location}, "
              f"trailer_size={self.trailer_size}, desired_gross={self.desired_gross}, desired_rpm={self.desired_rpm}, "
              f"active={self.active}, phone={self.phone}, states={self.states}")

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
        self.total_rpm = self.total_price / self.milage

class RouteBuilder:
    def __init__(self, driver_id: int, db: Session):
        self.driver = Driver(driver_id)
        self.db = db

    def get_top_loads(self, origin) -> List[LoadModel]:
        try:
            loads = (
                self.db.query(LoadModel)
                .filter(
                    LoadModel.pickup_location == origin,
                )
                .order_by(LoadModel.price.desc())
                .all()
            )
            
            return loads  
        except Exception as e:
            print(f"Error fetching loads from database: {e}")
            return []

    def generate_one_car_trailer_routes(self):
        try:
          
            top_loads = self.get_top_loads(self.driver.location)
            routes = []
            for top_load in top_loads:
                try:
                    second_pickup_loads = self.get_top_loads(top_load.delivery_location)
                    for secondary_load in second_pickup_loads:

                        route = Route(self.driver)
                        route.add_load(top_load)
                        route.add_load(secondary_load)
                        if (
                            route.total_price > float(self.driver.desired_gross)
                            and route.total_rpm > float(self.driver.desired_rpm)
                        ):
                            routes.append(route)
                except Exception as e:
                    print(f"Error processing secondary loads: {e}")
                    continue
            return routes
        except Exception as e:
            print(f"Error generating routes: {e}")
            return []

    def generate_two_car_trailer_routes(self):
        try:
            top_loads = self.get_top_loads(self.driver.location)
            routes = []
            for top_load in top_loads:
                try:
                    second_pickup_loads = self.get_top_loads(top_load.pickup_location)
                    for secondary_load in second_pickup_loads:
                        route = Route(self.driver)
                        route.add_load(top_load)
                        route.add_load(secondary_load)
                        if (
                            route.total_price > float(self.driver.desired_gross)
                            and route.total_rpm > float(self.driver.desired_rpm)
                        ):
                            routes.append(route)
                except Exception as e:
                    print(f"Error processing secondary loads: {e}")
                    continue
            return routes
        except Exception as e:
            print(f"Error generating routes: {e}")
            return []

    def save_route_to_db(self, route: Route):
        try:
            new_route = RouteModel(
                driver_id=self.driver.driver_id,
                loads=route.load_ids,
                milage=route.milage,
                total_rpm=route.total_rpm,
                total_price=route.total_price,
            )
            self.db.add(new_route)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            print(f"Error saving route to database: {e}")
            raise