
from resources.models import DriverModel, get_db, RouteModel
from sqlalchemy.orm import Session
from resources.classes import RouteBuilder  # Assuming RouteBuilder is defined in another file

def build_routes_for_active_drivers():
    db: Session = next(get_db())

    try:
        # Fetch active drivers from the database
        active_driver_ids = db.query(DriverModel.driver_id).filter(DriverModel.active.is_(True)).all()

        for driver_id, in active_driver_ids:  # Note the comma to unpack the tuple

            routes = []
            
            # Create a RouteBuilder instance for the driver
            builder = RouteBuilder(driver_id, db)
            trailer_size = int(getattr(builder.driver, 'trailer_size', 0))

            if trailer_size == 1:  
                routes = builder.generate_one_car_trailer_routes()
            if trailer_size == 2: 
                routes = builder.generate_two_car_trailer_routes()
            if trailer_size == 3:
                routes = builder.generate_three_car_trailer_routes()
                print('generated')

            print(routes)
            db_routes = db.query(RouteModel).filter_by(driver_id=driver_id).all()
            for route in routes:
                if route not in db_routes:
                    print(f"Saving route for driver {driver_id}: {route}")
                    builder.save_route_to_db(route)

    except Exception as e:
        print(f"Error building routes for active drivers: {e}")

    finally:
        db.close()


if __name__ == "__main__":
    build_routes_for_active_drivers()

