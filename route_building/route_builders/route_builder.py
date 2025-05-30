from resources.models import DriverModel, LoadModel, get_db
from sqlalchemy.orm import Session
from ..api.graphhopper_api_client import GraphhopperApiClient
from ..api.pelias_api_client import PeliasApiClient
from ..driver import Driver
from ..route import Route
from typing import List
import json
from ..workers.full_route_worker import FullRouteWorker  # Assuming this is defined in another file
from ..workers.top_loads_worker import TopLoadsWorker  # Assuming this is defined in another file

class RouteBuilder:
    def __init__(self, db: Session):
        self.db = db
        self.gh_client = GraphhopperApiClient()
        self.pl_client = PeliasApiClient()
        self.full_route_worker = FullRouteWorker(self.pl_client, self.gh_client)
        self.top_loads_worker = TopLoadsWorker(self.pl_client, db)

    def find_top_loads_within_radius_miles(self, origin: str, radius: float = 50.0) -> List[LoadModel]:
        self.top_loads_worker.find_top_loads_within_radius_miles(origin, radius)
       
    def calculate_full_route_length(self, route: Route) -> float:
        self.full_route_worker.calculate_full_route_length(route)