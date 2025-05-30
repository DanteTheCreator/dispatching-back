from resources.models import DriverModel, LoadModel, get_db
from sqlalchemy.orm import Session
from resources.classes import RouteBuilder  # Assuming RouteBuilder is defined in another file
from ..api.graphhopper_api_client import GraphhopperApiClient
from ..api.pelias_api_client import PeliasApiClient
from ..driver import Driver
from ..route import Route
from typing import List
from sqlalchemy import cast, text

class RouteBuilder:
    def __init__(self, driver_id: int, db: Session):
        self.driver = Driver(driver_id)
        self.db = db
        self.gh_client = GraphhopperApiClient()
        self.pl_client = PeliasApiClient()

    def __find_loads_within_radius(self, origin: str, radius: float = 80467.2) -> List[LoadModel]:
        print(f"Finding loads within {radius} meters of origin: {origin}")
        pelias_response = self.pl_client.get(origin)
        coords = pelias_response.json().get('features', [])[0].get('geometry', {}).get('coordinates', [])

        if not coords or len(coords) < 2:
            print(f"Invalid coordinates for origin {origin}: {coords}")
            return []

        try:
            sql = text("""
                SELECT 
                *,           
                ST_AsGeoJSON(pickup_points) as pickup_point_json
                FROM loads
                WHERE ST_DWithin(
                    pickup_points::geography,
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                    :distance
                )
                ORDER BY price DESC
                """)

            result = self.db.execute(
                sql,
                {
                    'lon': coords[0],
                    'lat': coords[1],
                    'distance': radius
                }
            )

            loads = result.fetchall()
            return loads  # type: ignore
        except Exception as e:
            print(f"Error fetching loads from database: {e}")
            return []
        



    def get_top_loads(self, origin) -> List[LoadModel]:
        print(f"get_top_loads called with origin: {origin}")
        pelias_response = self.pl_client.get(origin)
        coords = pelias_response.json().get('features', [])[0].get('geometry', {}).get('coordinates', [])


        try:
            # Assuming you have GeoAlchemy2 properly imported and set up
            sql = text("""
                SELECT 
                *,           
                ST_AsGeoJSON(pickup_points) as pickup_point_json
                FROM loads
                WHERE ST_DWithin(
                    pickup_points::geography,
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                    :distance
                )
                ORDER BY price DESC
                """)

            # Execute the query with parameters
            result = self.db.execute(
                sql,
                {
                    'lon': coords[0],
                    'lat': coords[1],
                    'distance': 80467.2
                }
            )

            # Fetch all results as dictionaries
            loads = result.fetchall()
            return loads  # type: ignore
        except Exception as e:
            print(f"Error fetching loads from database: {e}")
            return []
        
    def get_driver_coordinates(self) -> List[float]:
        try:
            driver_geo = self.pl_client.get(self.driver.location)
            driver_features = driver_geo.json().get('features', [])
            if not driver_features:
                print(f"No features found for driver location: {self.driver.location}")
                return []
            driver_points = driver_features[0]['geometry']['coordinates']
            if not isinstance(driver_points, list) or len(driver_points) != 2:
                print(f"Invalid coordinates for driver location: {driver_points}")
                return []
            return [driver_points]
        except Exception as e:
            print(f"Error getting driver coordinates: {e}")
            return []
        
    def get_pickup_point(self, load) -> List[float] | None:
    
        pickup_json = None
        try:
            if hasattr(load, 'pickup_point_json'):
                pickup_json = load.pickup_point_json
            elif hasattr(load, '_asdict') and 'pickup_point_json' in load._asdict():
                pickup_json = load._asdict()['pickup_point_json']
            elif isinstance(load, dict) or hasattr(load, '__getitem__'):
                pickup_json = load['pickup_point_json']
        except Exception as e:
            print(f"Error accessing pickup_point_json: {e}")
            
        if not pickup_json:
            print(f"Missing pickup coordinates for load {getattr(load, 'load_id', 'unknown')}")
            return None
            
        try:
            if isinstance(pickup_json, str):
                import json
                pickup_coords = json.loads(pickup_json).get('coordinates')
            else:
                pickup_coords = pickup_json.get('coordinates') if isinstance(pickup_json, dict) else None
                
            if not pickup_coords or not isinstance(pickup_coords, list) or len(pickup_coords) != 2:
                print(f"Invalid pickup coordinates for load {getattr(load, 'load_id', 'unknown')}: {pickup_coords}")
                return None
                
            return pickup_coords
        except Exception as e:
            print(f"Error parsing pickup coordinates: {e}")
            return None

    def get_delivery_point(self, load) -> List[float] | None:
        """Extract delivery coordinates from a load object."""
        try:
            delivery_location = None
            if isinstance(load, dict):
                delivery_location = load.get('delivery_location')
            elif hasattr(load, '_asdict'):
                delivery_location = load._asdict().get('delivery_location')
            elif hasattr(load, 'delivery_location'):
                delivery_location = load.delivery_location
                
            if not delivery_location:
                print(f"No delivery location found for load {getattr(load, 'load_id', 'unknown')}")
                return None
                
            delivery_geo = self.pl_client.get(delivery_location.split()[-1])
            delivery_features = delivery_geo.json().get('features', [])
            
            if not delivery_features:
                print(f"No features found for delivery location: {delivery_location}")
                return None
                
            delivery_points = delivery_features[0]['geometry']['coordinates']
            
            if not delivery_points or not isinstance(delivery_points, list) or len(delivery_points) != 2:
                print(f"Invalid delivery coordinates for load {getattr(load, 'load_id', 'unknown')}: {delivery_points}")
                return None
                
            return delivery_points
        except Exception as e:
            print(f"Error getting delivery coordinates: {e}")
            return None
        
    def get_graphhopper_distance_miles(self, points):
        payload = {'profile': 'car', 'points': points}
        try:
            response = self.gh_client.post(url='route', payload=payload)
        except Exception as e:
            print(f"Error making request to GraphHopper: {e}")
            return 1.0
        if not response or not hasattr(response, 'json'):
            print("Invalid response from GraphHopper API")
            return 1.0

        try:
            # Check if response has content
            if hasattr(response, 'text'):
                if not response.text or not response.text.strip():
                    print("Graphhopper response is empty!")
                    return 0
            response_json = response.json()
        except Exception as e:
            print(f"Failed to parse API response as JSON: {str(e)}")
            if hasattr(response, 'text'):
                print("Graphhopper raw response:", response.text)
            return 1.0
        if 'paths' not in response_json:
            print(f"Response missing 'paths' key: {response_json}")
            return 1.0
        if not response_json['paths']:
            print("Empty paths array in response")
            return 1.0
        try:
            distance = response_json['paths'][0]['distance']
            distance_miles = distance / 1609.34  # Convert meters to miles
            return max(distance_miles, 1.0)
        except Exception as e:
            print(f"Error extracting distance from response: {e}")
            return 1.0

    def calculate_full_route_length(self, route: Route) -> float:
        try:
            points = self.get_driver_coordinates()

            pickups = []
            deliveries = []

            for load in route.loads:
                # Get pickup point
                pickup_coords = self.get_pickup_point(load)
                if pickup_coords:
                    pickups.append(pickup_coords)

                # Get delivery point
                delivery_coords = self.get_delivery_point(load)
                if delivery_coords:
                    deliveries.append(delivery_coords)

            points.extend(pickups)
            points.extend(deliveries)
            print(f"Full route points: {points}")
            if len(points) < 2:
                print("Not enough valid points to calculate a route")
                return 1.0
            
            graphhopper_distance = self.get_graphhopper_distance_miles(points)
            return graphhopper_distance
        except Exception as e:
            print(f"Error calculating route length: {str(e)}")
            return 1.0  # Return a minimal non-zero value on error







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
                
            for route in routes:
                builder.save_route_to_db(route)

    except Exception as e:
        print(f"Error building routes for active drivers: {e}")

    finally:
        db.close()


if __name__ == "__main__":
    build_routes_for_active_drivers()

