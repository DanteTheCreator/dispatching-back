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
    
    @staticmethod
    def build_one_car_glink(loads):
         # Construct the Google Maps route link
        base_url = "https://www.google.com/maps/dir/"
        locations = []
        
        for load in loads:
            locations.append(load['pickup_location'])
            locations.append(load['delivery_location'])

        google_maps_link = base_url + "/".join(locations)
        return google_maps_link
    
    @staticmethod
    def build_multiple_car_glink(loads):
        # For three-car: pickups first, then deliveries
        base_url = "https://www.google.com/maps/dir/"
        pickup_locations = [load['pickup_location'] for load in loads]
        delivery_locations = [load['delivery_location'] for load in loads]
        locations = pickup_locations + delivery_locations
        google_maps_link = base_url + "/".join(locations)
        return google_maps_link