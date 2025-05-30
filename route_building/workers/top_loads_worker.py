from sqlalchemy import cast, text

class TopLoadsWorker:

    def __init__(self, pl_client, db):
        self.pl_client = pl_client
        self.db = db

    def find_top_loads_within_radius_miles(self, origin: str, radius: float = 50.0):
        print(f"Finding loads within {radius} miles of origin: {origin}")
        pelias_response = self.pl_client.get(origin)
        coords = pelias_response.json().get('features', [])[0].get('geometry', {}).get('coordinates', [])

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
                ORDER BY price DESC
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