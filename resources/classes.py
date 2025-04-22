
from resources.models import DriverModel, RouteModel, get_db, LoadModel
from sqlalchemy.orm import Session
from typing import List
import logging
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import cast, text
from selenium_agency.handlers import PeliasHandler, GraphhopperHandler
from sqlalchemy import func

# Set up logging
logger = logging.getLogger('dispatching_api')
logger.setLevel(logging.INFO)

# File handler for saving logs to file
# Specify your log file path here
file_handler = logging.FileHandler('classes.log')
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

gh_handler = GraphhopperHandler()
pl_handler = PeliasHandler()


# def convert_postgis_to_coords(geom_string):
#     # Convert hex string to binary
#     binary = binascii.unhexlify(geom_string[2:])  # Skip the '0x' prefix

#     # Parse the binary WKB to a shapely geometry
#     point = wkb.loads(binary)

#     # Return as [longitude, latitude]
#     return [point.x, point.y]

class Driver:
    def __init__(self, driver_id):
        self.driver_id = driver_id
        self.db = next(get_db())

        # Get driver info from database
        driver = self.db.query(DriverModel).filter(
            DriverModel.driver_id == self.driver_id).first()
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
        origin = pl_handler.get(origin).json()[
            'features'][0]['geometry']['coordinates']
        print(f"Origin coordinates: {origin}")
        try:
            # Assuming you have GeoAlchemy2 properly imported and set up
            sql = text("""
                SELECT 
                *,           
                ST_AsGeoJSON(pickup_points) as pickup_point_json
                FROM loads
                WHERE ST_DWithin(
                    pickup_points,
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326),
                    :distance
                )
                ORDER BY price DESC
                """)

            # Execute the query with parameters
            result = self.db.execute(
                sql,
                {
                    'lon': origin[0],
                    'lat': origin[1],
                    'distance': 80467.2
                }
            )

            # Fetch all results as dictionaries
            loads = result.fetchall()
            return loads  # type: ignore
        except Exception as e:
            logger.info(f"Error fetching loads from database: {e}")
            return []

    def calculate_full_route_length(self, route: Route) -> float:
        driver_points = pl_handler.get(self.driver.location).json()[
            'features'][0]['geometry']['coordinates']
        points = [[driver_points[1], driver_points[0]]]

        for load in route.loads:
            coords = load.pickup_points_json['coordinates']
            points.append(coords)
        print(points)
        return gh_handler.post(url='route', payload={'profile': 'car', 'points': points}).json()['paths'][0]['distance']

    def generate_one_car_trailer_routes(self, limit: int = 10):
        try:
            top_loads = self.get_top_loads(self.driver.location)
            logger.info(f"Top loads found: {len(top_loads)}")

            routes = []
            for top_load in top_loads[:3]:
                if len(routes) >= limit:
                    break
                try:
                    second_pickup_loads = self.get_top_loads(
                        top_load.delivery_location.split()[-1])
                    for secondary_load in second_pickup_loads[:3]:
                        if len(routes) >= limit:
                            break
                        route = Route(self.driver)
                        route.add_load(top_load)
                        route.add_load(secondary_load)
                        if top_load == secondary_load:
                            continue

                        # Calculate accurate route length
                        try:
                            accurate_milage = self.calculate_full_route_length(
                                route)
                            route.milage = accurate_milage / 1000  # Convert meters to kilometers
                            route.total_rpm = route.total_price / route.milage
                        except Exception as e:
                            logger.info(f"Error calculating route length: {e}")
                            continue

                        if (
                            route.total_price > float(
                                self.driver.desired_gross)
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
            for top_load in top_loads[:3]:
                if len(routes) >= limit:
                    break
                try:
                    second_pickup_loads = self.get_top_loads(
                        top_load.pickup_location.split()[-1])
                    for secondary_load in second_pickup_loads[1:3]:
                        if len(routes) >= limit:
                            break
                        route = Route(self.driver)
                        route.add_load(top_load)
                        route.add_load(secondary_load)
                        if top_load == secondary_load:
                            print('Same')
                            continue

                        # Calculate accurate route length
                        try:
                            accurate_milage = self.calculate_full_route_length(
                                route)
                            route.milage = accurate_milage / 1000  # Convert meters to kilometers
                            route.total_rpm = route.total_price / route.milage
                        except Exception as e:
                            logger.info(f"Error calculating route length: {e}")
                            continue

                        if (
                            route.total_price > float(
                                self.driver.desired_gross)
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

    def generate_three_car_trailer_routes(self, limit: int = 10):
        try:
            top_loads = self.get_top_loads(self.driver.location)
            print(f"Top loads found: {len(top_loads)}")

            routes = []
            for top_load in top_loads[:5]:
                if len(routes) >= limit:
                    break
                try:
                    second_pickup_loads = self.get_top_loads(
                        top_load.delivery_location.split()[-1])
                    for secondary_load in second_pickup_loads[1:5]:
                        if len(routes) >= limit:
                            break
                        try:
                            third_pickup_loads = self.get_top_loads(
                                secondary_load.delivery_location.split()[-1])
                            for tertiary_load in third_pickup_loads[2:5]:
                                if len(routes) >= limit:
                                    break
                                route = Route(self.driver)
                                route.add_load(top_load)
                                route.add_load(secondary_load)
                                route.add_load(tertiary_load)
                                print('Route Price: ' , route.total_price)
                                # Avoid duplicate loads
                                if top_load == secondary_load or secondary_load == tertiary_load or top_load == tertiary_load:
                                    continue

                                # Calculate accurate route length
                                try:
                                    accurate_milage = self.calculate_full_route_length(
                                        route)
                                    route.milage = accurate_milage / 1000  # Convert meters to kilometers
                                    route.total_rpm = route.total_price / route.milage
                                except Exception as e:
                                    logger.info(
                                        f"Error calculating route length: {e}")
                                    continue

                                if (
                                    route.total_price > float(self.driver.desired_gross) and
                                        route.total_rpm > float(self.driver.desired_rpm)):

                                    routes.append(route)
                                    routes.sort(
                                        key=lambda r: r.efficiency_score, reverse=True)
                        except Exception as e:
                            logger.info(
                                f"Error processing tertiary loads: {e}")
                            continue
                except Exception as e:
                    logger.info(f"Error processing secondary loads: {e}")
                    continue

            logger.info(
                f"Generated {len(routes)} three-car routes that meet criteria")
            return routes[:limit]
        except Exception as e:
            print(f"Error generating routes: {e}")
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
                logger.info(
                    "Driver already has over 10 routes. Not adding any more.")
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


