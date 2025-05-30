import sys
import os
# Add the parent directory to the Python path to find the resources module
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from resources.models import DriverModel, LoadModel, get_db
from sqlalchemy.orm import Session
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api.graphhopper_api_client import GraphhopperApiClient
from api.pelias_api_client import PeliasApiClient
from driver import Driver
from route import Route
from typing import List
import json
from workers.full_route_worker import FullRouteWorker
from workers.top_loads_worker import TopLoadsWorker

class RouteBuilder:
    def __init__(self, db: Session):
        self.db = db
        self.gh_client = GraphhopperApiClient()
        self.pl_client = PeliasApiClient()
        self.full_route_worker = FullRouteWorker(self.pl_client, self.gh_client)
        self.top_loads_worker = TopLoadsWorker(self.pl_client, db)

    def find_top_loads_within_radius_miles(self, origin: str) -> List[LoadModel]:
        # Use the same method as find_top_loads_within_radius_miles for consistency
        return self.top_loads_worker.find_top_loads_within_radius_miles(origin, 50.0)
       
    def calculate_full_route_length(self, route: Route) -> float:
        return self.full_route_worker.calculate_full_route_length(route)