import sys
import os
# Add the parent directory to the Python path to find the resources module
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from route import Route
import json

class FullRouteWorker:

    def __init__(self, pl_client, gh_client):
        self.pl_client = pl_client
        self.gh_client = gh_client

    def get_pickup_point(self, load):
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

    def get_delivery_point(self, load):
        """Extract delivery coordinates from a load object."""
        # First try to get delivery coordinates from stored delivery_points (similar to pickup_points)
        delivery_json = None
        try:
            # Check if delivery_point_json exists (if load has it)
            if hasattr(load, 'delivery_point_json'):
                delivery_json = load.delivery_point_json
            elif hasattr(load, '_asdict') and 'delivery_point_json' in load._asdict():
                delivery_json = load._asdict()['delivery_point_json']
            elif isinstance(load, dict) and 'delivery_point_json' in load:
                delivery_json = load['delivery_point_json']
        except Exception as e:
            print(f"Error accessing delivery_point_json: {e}")
            
        # If we have stored delivery coordinates, use them
        if delivery_json:
            try:
                if isinstance(delivery_json, str):
                    delivery_coords = json.loads(delivery_json).get('coordinates')
                else:
                    delivery_coords = delivery_json.get('coordinates') if isinstance(delivery_json, dict) else None
                    
                if delivery_coords and isinstance(delivery_coords, list) and len(delivery_coords) == 2:
                    return delivery_coords
            except Exception as e:
                print(f"Error parsing stored delivery coordinates: {e}")
        
        # Fallback to Pelias API call
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

    def get_driver_coordinates(self, route):
        try:
            driver_geo = self.pl_client.get(route.driver.location)
            driver_features = driver_geo.json().get('features', [])
            if not driver_features:
                print(f"No features found for driver location: {route.driver.location}")
                return []
            driver_points = driver_features[0]['geometry']['coordinates']
            if not isinstance(driver_points, list) or len(driver_points) != 2:
                print(f"Invalid coordinates for driver location: {driver_points}")
                return []
            return [driver_points]
        except Exception as e:
            print(f"Error getting driver coordinates: {e}")
            return []

    def get_full_route_points(self, route):
        """
        Get route points for single car routes (sequential pickup/delivery).
        Pattern: [driver, pickup1, delivery1, pickup2, delivery2, ...]
        """
        points = self.get_driver_coordinates(route)

        for load in route.loads:
            # Get pickup point
            pickup_coords = self.get_pickup_point(load)
            if pickup_coords:
                points.append(pickup_coords)

            # Get delivery point
            delivery_coords = self.get_delivery_point(load)
            if delivery_coords:
                points.append(delivery_coords)

        return points

    def get_full_route_points_multiple_car(self, route):
        """
        Get route points optimized for multiple car routes.
        This matches the pattern used by build_multiple_car_glink:
        [driver, pickup1, pickup2, pickup3, delivery1, delivery2, delivery3]
        """
        points = self.get_driver_coordinates(route)
        
        # Collect all pickup points first
        pickup_points = []
        delivery_points = []
        
        for load in route.loads:
            # Get pickup point
            pickup_coords = self.get_pickup_point(load)
            if pickup_coords:
                pickup_points.append(pickup_coords)
            
            # Get delivery point
            delivery_coords = self.get_delivery_point(load)
            if delivery_coords:
                delivery_points.append(delivery_coords)
        
        # Add pickups first, then deliveries
        points.extend(pickup_points)
        points.extend(delivery_points)
        
        return points
    
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
        """
        Calculate route length using the appropriate method based on number of loads.
        For multiple loads (2+), use multiple car logic to match build_multiple_car_glink.
        """
        try:
            # Determine which route logic to use based on number of loads
            if len(route.loads) >= 2:
                # Use multiple car logic for routes with 2+ loads
                full_route_points = self.get_full_route_points_multiple_car(route)
                print(f"Multiple car route points: {full_route_points}")
            else:
                # Use single car logic for single load routes
                full_route_points = self.get_full_route_points(route)
                print(f"Single car route points: {full_route_points}")
                
            if len(full_route_points) < 2:
                print("Not enough valid points to calculate a route")
                return 1.0
            
            graphhopper_distance = self.get_graphhopper_distance_miles(full_route_points)
            return graphhopper_distance
        except Exception as e:
            print(f"Error calculating route length: {str(e)}")
            return 1.0  # Return a minimal non-zero value on error
