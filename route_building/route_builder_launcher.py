from ..resources.models import DriverModel, get_db
from sqlalchemy.orm import Session
from route_builder_manager import RouteBuilderManager

def build_routes_for_active_drivers():
    db: Session = next(get_db())
    route_builder_manager = RouteBuilderManager(db)
    route_builder_manager.build_routes_for_active_drivers()

if __name__ == "__main__":
    build_routes_for_active_drivers()

