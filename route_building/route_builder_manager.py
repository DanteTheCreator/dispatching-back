from .driver import Driver
from route_builders.route_builder_one_car import RouteBuilderOneCar
from route_builders.route_builder_two_car import RouteBuilderTwoCar
from route_builders.route_builder_three_car import RouteBuilderThreeCar
from ..resources.models import DriverModel
from resources.models import RouteModel
from .route import Route
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import cast, text



class RouteBuilderManager:
    def __init__(self, db):
        self.db = db

        self.one_car_builder = RouteBuilderOneCar(db)
        self.two_car_builder = RouteBuilderTwoCar(db)
        self.three_car_builder = RouteBuilderThreeCar(db)

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
            print(f"Error saving route to database: {e}")
            raise

    def build_routes_for_active_drivers(self):
        try:
            # Fetch active drivers from the database
            active_driver_ids = self.db.query(DriverModel.driver_id).filter(DriverModel.active.is_(True)).all()

            for driver_id, in active_driver_ids:  # Note the comma to unpack the tuple
                driver = Driver(driver_id)
                trailer_size = int(getattr(driver, 'trailer_size', 0))
                routes = []

                if trailer_size == 1:  
                    routes = self.one_car_builder.build_routes(driver)
                if trailer_size == 2: 
                    routes = self.two_car_builder.build_routes(driver)
                if trailer_size == 3:
                    routes = self.three_car_builder.build_routes(driver)

                print(routes)
                    
                db_routes = self.db.query(RouteModel).filter_by(driver_id=driver_id).all()
                for route in routes:
                    if route not in db_routes:
                        print(f"Saving route for driver {driver_id}: {route}")
                        self.save_route_to_db(route)

        except Exception as e:
            print(f"Error building routes for active drivers: {e}")

        finally:
            self.db.close()
    