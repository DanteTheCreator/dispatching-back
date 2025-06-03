import sys
import os
# Add the parent directory to the Python path to find the resources module
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from route import Route
from route_builders.route_builder import RouteBuilder
from driver import Driver
from sqlalchemy.orm import Session

class RouteBuilderTwoCar(RouteBuilder):
    def __init__(self, db: Session):
        super().__init__(db)  # Call parent constructor to initialize workers and API clients

    def build_glink(self, loads):
         # Construct the Google Maps route link
        base_url = "https://www.google.com/maps/dir/"
        locations = []
        
        for load in loads:
            locations.append(load.pickup_location)
            locations.append(load.delivery_location)

        google_maps_link = base_url + "/".join(locations)
        return google_maps_link

    def build_routes(self, driver, limit: int = 10):
        try:
            top_loads = self.find_top_loads_within_radius_miles(driver.location)
            routes = []
            for top_load in top_loads[:10]:
                if len(routes) >= limit:
                    break
                try:
                    # Use delivery_location or another field as appropriate
                    next_location = top_load.pickup_location.split()[-1] if top_load.pickup_location is not None else None
                    if not next_location:
                        continue
                    second_pickup_loads = self.find_top_loads_within_radius_miles(next_location)
                    for secondary_load in second_pickup_loads[:10]:
                        if len(routes) >= limit:
                            break
                        # Prevent duplicate loads
                        if (
                            getattr(top_load, 'price', 0) == getattr(secondary_load, 'price', 0) and
                            getattr(top_load, 'milage', 0) == getattr(secondary_load, 'milage', 0) and
                            getattr(top_load, 'pickup_location', '') == getattr(secondary_load, 'pickup_location', '') and
                            getattr(top_load, 'delivery_location', '') == getattr(secondary_load, 'delivery_location', '')
                        ):
                            print('Same')
                            continue
                        route = Route(driver)
                        route.add_load(top_load)
                        route.add_load(secondary_load)
                        # Calculate accurate route length
                        try:
                            accurate_milage = self.calculate_full_route_length(
                                route)
                            if accurate_milage is None or accurate_milage == 1.0:
                                raise ValueError("Couldn't calculate accurate mileage, one of the loads is probably outside of US")
                            print('GH Responded with: ', accurate_milage)
                            route.milage = accurate_milage
                            try:
                                if route.milage > 0:
                                    route.total_rpm = route.total_price / route.milage
                                else:
                                    route.total_rpm = 0
                                    print("Zero mileage detected, setting RPM to zero")
                                
                            except Exception as e:
                                print(f"Error calculating RPM: {str(e)}")
                                route.total_rpm = 0
                        except Exception as e:
                            print(f"Error calculating route length: {e}")
                            continue

                        if (
                            route.total_price > float(
                                driver.desired_gross)
                            and route.total_rpm > float(driver.desired_rpm)
                            and route.milage < float(driver.max_milage)
                        ):
                            routes.append(route)
                except Exception as e:
                    print(f"Error processing secondary loads: {e}")
                    continue
            return routes
        except Exception as e:
            print(f"Error generating routes: {e}")
            return []