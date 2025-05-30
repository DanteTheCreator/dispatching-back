from sqlalchemy import cast, text

class TopLoadsWorker:

    def __init__(self, pl_client, db):
        self.pl_client = pl_client
        self.db = db

    def find_top_loads_within_radius_miles(self, origin: str, radius: float = 50.0):
        print(f"Finding loads within {radius} miles of origin: {origin}")
        
        try:
            pelias_response = self.pl_client.get(origin)
            
            # Check if response is valid
            if not pelias_response or pelias_response.status_code != 200:
                print(f"Failed to get valid response from Pelias API. Status: {getattr(pelias_response, 'status_code', 'No response')}")
                return []
            
            # Parse JSON response safely
            try:
                response_data = pelias_response.json()
            except Exception as json_error:
                print(f"Failed to parse JSON response: {json_error}")
                return []
            
            features = response_data.get('features', [])
            if not features:
                print(f"No features found in Pelias response for origin: {origin}")
                return []
                
            coords = features[0].get('geometry', {}).get('coordinates', [])
            
        except Exception as api_error:
            print(f"Error connecting to Pelias API: {api_error}")
            # For now, return empty list when API is unavailable
            # In production, you might want to use a fallback geocoding service
            return []

        if not coords or len(coords) < 2:
            print(f"Invalid coordinates for origin {origin}: {coords}")
            return []

        try:
            # Convert miles to meters for PostGIS ST_DWithin function
            distance_meters = radius * 1609.34
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
            ORDER BY created_at DESC, price DESC
            """)

            result = self.db.execute(
                sql,
                {
                    'lon': coords[0],
                    'lat': coords[1],
                    'distance': distance_meters
                }
            )

            loads = result.fetchall()
            return loads  # type: ignore
        except Exception as e:
            print(f"Error fetching loads from database: {e}")
            return []