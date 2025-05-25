from resources.models import DriverModel, RouteModel, get_db, LoadModel
from sqlalchemy.orm import Session
from typing import List
import logging
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import cast, text
from selenium_agency.api.handlers import PeliasHandler, GraphhopperHandler

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
            self.max_milage = float(getattr(driver, 'max_milage', 0.0))
            self.desired_rpm = float(getattr(driver, 'desired_rpm', 0.0))
            self.active = driver.active
            self.phone = driver.phone
            self.states = driver.states if driver.states is not None else []
        except (ValueError, TypeError, AttributeError) as e:
            print(f"Error converting values: {e}")
            self.desired_gross = 0.0
            self.desired_rpm = 0.0

        # print(f"Driver attributes: driver_id={self.driver_id}, full_name={self.full_name}, location={self.location}, "
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
        try:
            if self.milage > 0:
                self.total_rpm = self.total_price / self.milage
            else:
                self.total_rpm = 0
                logger.warning("Zero mileage detected, setting RPM to zero")
        except Exception as e:
            logger.error(f"Error calculating RPM: {str(e)}")
            self.total_rpm = 0


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
                    pickup_points::geography,
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
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
            print(f"Error fetching loads from database: {e}")
            print(f"Error fetching loads from database: {e}")
            return []

    def calculate_full_route_length(self, route: Route) -> float:
        try:
            # Start with driver's location
            driver_points = pl_handler.get(self.driver.location).json()['features'][0]['geometry']['coordinates']
            points = [driver_points]

            # First collect all loads' pickup and delivery points
            pickups = []
            deliveries = []
            
            for load in route.loads:
                # Get pickup point
                pickup_json = None
                if hasattr(load, 'pickup_point_json'):
                    pickup_json = load.pickup_point_json
                elif hasattr(load, '_asdict') and 'pickup_point_json' in load._asdict():
                    pickup_json = load._asdict()['pickup_point_json']
                elif isinstance(load, dict) or hasattr(load, '__getitem__'):
                    pickup_json = load['pickup_point_json']
                
                if not pickup_json:
                    print(f"Missing pickup coordinates for load {getattr(load, 'load_id', 'unknown')}")
                    continue

                # Parse pickup coordinates
                if isinstance(pickup_json, str):
                    import json
                    pickup_coords = json.loads(pickup_json)['coordinates']
                else:
                    pickup_coords = pickup_json['coordinates']
                pickups.append(pickup_coords)

                # Get delivery point with proper dictionary handling
                try:
                    delivery_location = None
                    if isinstance(load, dict):
                        delivery_location = load.get('delivery_location')
                    elif hasattr(load, '_asdict'):
                        delivery_location = load._asdict().get('delivery_location')
                    elif hasattr(load, 'delivery_location'):
                        delivery_location = load.delivery_location
                    
                    if delivery_location:
                        delivery_points = pl_handler.get(delivery_location.split()[-1]).json()['features'][0]['geometry']['coordinates']
                        deliveries.append(delivery_points)
                    else:
                        logger.error(f"No delivery location found for load")
                        continue
                except Exception as e:
                    logger.error(f"Error getting delivery coordinates: {str(e)}")
                    continue

            # Add all points in correct order:
            # First all pickups
            points.extend(pickups)
            # Then all deliveries
            points.extend(deliveries)
                    
            print(f"Full route points: {points}")            
            # Need at least 2 points for a valid route
            if len(points) < 2:
                logger.error("Not enough valid points to calculate a route")
                return 0
                
            # Make the API call with proper error handling
            payload = {'profile': 'car', 'points': points}
            response = gh_handler.post(url='route', payload=payload)
            
            # Debug logging
            print(f"API response status: {getattr(response, 'status_code', 'unknown')}")
            
            # Check if response is valid
            if not response or not hasattr(response, 'json'):
                logger.error("Invalid response from GraphHopper API")
                return 0
                
            # Parse JSON response
            try:
                response_json = response.json()
            except Exception as e:
                logger.error(f"Failed to parse API response as JSON: {str(e)}")
                return 0
            
            # Check for required structure in response
            if 'paths' not in response_json:
                logger.error(f"Response missing 'paths' key: {response_json}")
                return 0
                
            if not response_json['paths']:
                logger.error("Empty paths array in response")
                return 0
            
            distance = response_json['paths'][0]['distance']
            # Ensure we return at least a minimum distance to avoid division by zero
            return max(distance, 1.0)  # Return at least 1 meter
            
        except Exception as e:
            logger.error(f"Error calculating route length: {str(e)}")
            print(f"Error calculating route length: {str(e)}")
            return 1.0  # Return a minimal non-zero value on error

    def generate_one_car_trailer_routes(self, limit: int = 10):
        try:
            top_loads = self.get_top_loads(self.driver.location)
            print(f"Top loads found: {len(top_loads)}")
            print(f"Top loads found: {len(top_loads)}")

            routes = []
            for top_load in top_loads[:3]:
                if len(routes) >= limit:
                    break
                try:
                    next_location = top_load.delivery_location.split()[-1] if getattr(top_load, 'delivery_location', None) is not None else None
                    if not next_location:
                        continue
                    second_pickup_loads = self.get_top_loads(next_location)
                    for secondary_load in second_pickup_loads[:3]:
                        if len(routes) >= limit:
                            break
                        # Prevent duplicate loads
                        if getattr(top_load, 'load_id', None) == getattr(secondary_load, 'load_id', None):
                            print('Same')
                            continue
                        route = Route(self.driver)
                        route.add_load(top_load)
                        route.add_load(secondary_load)
                        # Calculate accurate route length
                        try:
                            accurate_milage = self.calculate_full_route_length(route)
                            route.milage = accurate_milage / 1000  # Convert meters to kilometers
                            try:
                                if route.milage > 0:
                                    route.total_rpm = route.total_price / route.milage
                                else:
                                    route.total_rpm = 0
                                    logger.warning("Zero mileage detected, setting RPM to zero")
                            except Exception as e:
                                logger.error(f"Error calculating RPM: {str(e)}")
                                route.total_rpm = 0
                        except Exception as e:
                            print(f"Error calculating route length: {e}")
                            print(f"Error calculating route length: {e}")
                            continue

                        if (
                            route.total_price > float(self.driver.desired_gross)
                            and route.total_rpm > float(self.driver.desired_rpm)
                        ):
                            routes.append(route)
                except Exception as e:
                    print(f"Error processing secondary loads: {e}")
                    print(f"Error processing secondary loads: {e}")
                    continue
            return routes
        except Exception as e:
            print(f"Error generating routes: {e}")
            print(f"Error generating routes: {e}")
            return []

    def generate_two_car_trailer_routes(self, limit: int = 10):
        try:
            top_loads = self.get_top_loads(self.driver.location)
            print("driver location", self.driver.location)
            routes = []
            for top_load in top_loads[:10]:
                if len(routes) >= limit:
                    break
                try:
                    # Use delivery_location or another field as appropriate
                    next_location = top_load.delivery_location.split()[-1] if top_load.delivery_location is not None else None
                    if not next_location:
                        continue
                    second_pickup_loads = self.get_top_loads(next_location)
                    for secondary_load in second_pickup_loads[:10]:
                        if len(routes) >= limit:
                            break
                        # Prevent duplicate loads
                        if getattr(top_load, 'load_id', None) == getattr(secondary_load, 'load_id', None):
                            print('Same')
                            continue
                        route = Route(self.driver)
                        route.add_load(top_load)
                        route.add_load(secondary_load)
                        # Calculate accurate route length
                        try:
                            accurate_milage = self.calculate_full_route_length(
                                route)
                            print('GH Responded with: ', accurate_milage)
                            route.milage = accurate_milage / 1609.34  # Convert meters to miles
                            try:
                                if route.milage > 0:
                                    route.total_rpm = route.total_price / route.milage
                                else:
                                    route.total_rpm = 0
                                    logger.warning("Zero mileage detected, setting RPM to zero")
                            except Exception as e:
                                logger.error(f"Error calculating RPM: {str(e)}")
                                route.total_rpm = 0
                        except Exception as e:
                            print(f"Error calculating route length: {e}")
                            continue

                        if (
                            route.total_price > float(
                                self.driver.desired_gross)
                            and route.total_rpm > float(self.driver.desired_rpm)
                            and route.milage < float(self.driver.max_milage)
                        ):
                            routes.append(route)
                except Exception as e:
                    print(f"Error processing secondary loads: {e}")
                    continue
            return routes
        except Exception as e:
            print(f"Error generating routes: {e}")
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
                    next_location_2 = top_load.delivery_location.split()[-1] if getattr(top_load, 'delivery_location', None) is not None else None
                    if not next_location_2:
                        continue
                    second_pickup_loads = self.get_top_loads(next_location_2)
                    for secondary_load in second_pickup_loads[1:5]:
                        if len(routes) >= limit:
                            break
                        # Prevent duplicate loads
                        if getattr(top_load, 'load_id', None) == getattr(secondary_load, 'load_id', None):
                            continue
                        try:
                            next_location_3 = secondary_load.delivery_location.split()[-1] if getattr(secondary_load, 'delivery_location', None) is not None else None
                            if not next_location_3:
                                continue
                            third_pickup_loads = self.get_top_loads(next_location_3)
                            for tertiary_load in third_pickup_loads[2:5]:
                                if len(routes) >= limit:
                                    break
                                # Avoid duplicate loads
                                if (getattr(top_load, 'load_id', None) == getattr(tertiary_load, 'load_id', None) or
                                    getattr(secondary_load, 'load_id', None) == getattr(tertiary_load, 'load_id', None)):
                                    continue
                                route = Route(self.driver)
                                route.add_load(top_load)
                                route.add_load(secondary_load)
                                route.add_load(tertiary_load)
                                print('Route Price: ' , route.total_price)
                                # Calculate accurate route length
                                try:
                                    accurate_milage = self.calculate_full_route_length(route)
                                    route.milage = accurate_milage / 1000  # Convert meters to kilometers
                                    try:
                                        if route.milage > 0:
                                            route.total_rpm = route.total_price / route.milage
                                        else:
                                            route.total_rpm = 0
                                            logger.warning("Zero mileage detected, setting RPM to zero")
                                    except Exception as e:
                                        logger.error(f"Error calculating RPM: {str(e)}")
                                        route.total_rpm = 0
                                except Exception as e:
                                    print(f"Error calculating route length: {e}")
                                    continue

                                if (
                                    route.total_price > float(self.driver.desired_gross) and
                                    route.total_rpm > float(self.driver.desired_rpm)):
                                    routes.append(route)
                                    routes.sort(key=lambda r: getattr(r, 'efficiency_score', 0), reverse=True)
                        except Exception as e:
                            print(f"Error processing tertiary loads: {e}")
                            continue
                except Exception as e:
                    print(f"Error processing secondary loads: {e}")
                    continue

            print(f"Generated {len(routes)} three-car routes that meet criteria")
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
                print(
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
                print("A similar route already exists in the database.")
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


