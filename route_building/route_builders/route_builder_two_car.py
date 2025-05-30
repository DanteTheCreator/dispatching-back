from .route_builder import RouteBuilder
from .route import Route

class RouteBuilderTwoCar(RouteBuilder):


    def build_routes(self, limit: int = 10):
        try:
            top_loads = self.get_top_loads(self.driver.location)
            routes = []
            for top_load in top_loads[:10]:
                if len(routes) >= limit:
                    break
                try:
                    # Use delivery_location or another field as appropriate
                    next_location = top_load.pickup_location.split()[-1] if top_load.pickup_location is not None else None
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
                            if accurate_milage is None or accurate_milage == 0:
                                raise ValueError("Accurate mileage is None or zero, cannot proceed")
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