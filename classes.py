from models import DriverModel, RouteModel, get_db, LoadModel
from sqlalchemy.orm import Session
from typing import List
import logging
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import cast

# Set up logging
logger = logging.getLogger('dispatching_api')
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


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
            self.desired_gross = float(getattr(driver, 'desired_gross', 0.0))  
            self.desired_rpm = float(getattr(driver, 'desired_rpm', 0.0)) 
            self.active = driver.active
            self.phone = driver.phone
            self.states = driver.states if driver.states is not None else []
        except (ValueError, TypeError, AttributeError) as e:
            logger.info(f"Error converting values: {e}")
            self.desired_gross = 0.0
            self.desired_rpm = 0.0
        
        # logger.info(f"Driver attributes: driver_id={self.driver_id}, full_name={self.full_name}, location={self.location}, "
        #       f"trailer_size={self.trailer_size}, desired_gross={self.desired_gross}, desired_rpm={self.desired_rpm}, "
        #       f"active={self.active}, phone={self.phone}, states={self.states}")

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
                    LoadModel.pickup_location.like(f'%{origin}%')  # Wildcard search
                )
                .order_by(LoadModel.price.desc())
                .all()
            )
            
            return loads  
        except Exception as e:
            logger.info(f"Error fetching loads from database: {e}")
            return []

    def generate_one_car_trailer_routes(self, limit: int = 10):
        try:
            top_loads = self.get_top_loads(self.driver.location)
            logger.info(f"Top loads found: {len(top_loads)}")

            routes = []
            for top_load in top_loads:
                if len(routes) >= limit:
                    break
                try:
                    second_pickup_loads = self.get_top_loads(top_load.delivery_location.split()[-1])
                    for secondary_load in second_pickup_loads:
                        if len(routes) >= limit:
                            break
                        route = Route(self.driver)
                        route.add_load(top_load)
                        route.add_load(secondary_load)
                        if (
                            route.total_price > float(self.driver.desired_gross)
                            and route.total_rpm > float(self.driver.desired_rpm)
                        ):
                            routes.append(route)
                except Exception as e:
                    logger.info(f"Error processing secondary loads: {e}")
                    continue
            return routes
        except Exception as e:
            logger.info(f"Error generating routes: {e}")
            return []

    def generate_two_car_trailer_routes(self, limit: int = 10):
        try:
            top_loads = self.get_top_loads(self.driver.location)
            routes = []
            for top_load in top_loads:
                if len(routes) >= limit:
                    break
                try:
                    second_pickup_loads = self.get_top_loads(top_load.pickup_location.split()[-1])
                    for secondary_load in second_pickup_loads:
                        if len(routes) >= limit:
                            break
                        route = Route(self.driver)
                        route.add_load(top_load)
                        route.add_load(secondary_load)
                        if (
                            route.total_price > float(self.driver.desired_gross)
                            and route.total_rpm > float(self.driver.desired_rpm)
                        ):
                            routes.append(route)
                except Exception as e:
                    logger.info(f"Error processing secondary loads: {e}")
                    continue
            return routes
        except Exception as e:
            logger.info(f"Error generating routes: {e}")
            return []

    def save_route_to_db(self, route: Route):
        try:
            # Check if the driver already has over 10 routes
            route_count = (
                self.db.query(RouteModel)
                .filter(RouteModel.driver_id == self.driver.driver_id)
                .count()
            )
            if route_count >= 10:
                logger.info("Driver already has over 10 routes. Not adding any more.")
                return

            # Check if a similar route already exists
            existing_route = (
                self.db.query(RouteModel)
                .filter(RouteModel.driver_id == self.driver.driver_id)
                .filter(RouteModel.loads == cast(route.load_ids, JSONB))
                .first()
            )
            if existing_route:
                logger.info("A similar route already exists in the database.")
                return

            # Save the new route to the database
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
            logger.error(f"Error saving route to database: {e}")
            raise