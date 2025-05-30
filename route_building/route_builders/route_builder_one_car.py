import sys
import os
# Add the parent directory to the Python path to find the resources module
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from route import Route
from route_builders.route_builder import RouteBuilder
from driver import Driver
from sqlalchemy.orm import Session

class RouteBuilderOneCar(RouteBuilder):
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
            for top_load in top_loads[:3]:
                if len(routes) >= limit:
                    break
                try:
                    next_location = top_load.delivery_location.split()[-1] if getattr(top_load, 'delivery_location', None) is not None else None
                    if not next_location:
                        continue
                    second_pickup_loads = self.find_top_loads_within_radius_miles(next_location)
                    for secondary_load in second_pickup_loads[:3]:
                        if len(routes) >= limit:
                            break
                        # Prevent duplicate loads
                        if getattr(top_load, 'load_id', None) == getattr(secondary_load, 'load_id', None):
                            print('Same')
                            continue
                        route = Route(driver)
                        route.add_load(top_load)
                        route.add_load(secondary_load)
                        # Calculate accurate route length
                        try:
                            accurate_milage = self.calculate_full_route_length(route)
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
                            route.total_price > float(driver.desired_gross)
                            and route.total_rpm > float(driver.desired_rpm)
                        ):
                            routes.append(route)
                except Exception as e:
                    print(f"Error processing secondary loads: {e}")
                    continue
            return routes
        except Exception as e:
            print(f"Error generating routes: {e}")
            return []