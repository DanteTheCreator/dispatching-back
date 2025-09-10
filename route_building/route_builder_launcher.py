import sys
import os
import time
# Add the parent directory to the Python path to find the resources module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from resources.models import get_db
from sqlalchemy.orm import Session
from route_builder_manager import RouteBuilderManager

def build_routes_for_active_drivers():
    while True:
        db: Session = next(get_db())
        try:
            route_builder_manager = RouteBuilderManager(db)
            route_builder_manager.build_routes_for_active_drivers()
        finally:
            db.close()
        time.sleep(300)

if __name__ == "__main__":
    build_routes_for_active_drivers()

