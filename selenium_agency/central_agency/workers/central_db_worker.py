from geoalchemy2.elements import WKTElement
import time
from resources.models import LoadModel, get_db

class CentralDbWorker:
    def __init__(self):
        self.__db_Session = next(get_db())

    def __format_and_get_load_model(self, load):
        if not load:
            return None

        try:
            pickup_location = f"{load['origin']['city']}, {load['origin']['state']} {load['origin']['zip']}"
            delivery_location = f"{load['destination']['city']}, {load['destination']['state']} {load['destination']['zip']}"

            pickup_coordinates = [load['origin']['geoCode']
                                  ['longitude'], load['origin']['geoCode']['latitude']]
            delivery_coordinates = [load['destination']['geoCode']
                                    ['longitude'], load['destination']['geoCode']['latitude']]
        except KeyError as e:
            print(f"KeyError: {e} in load data: {load}")
            return None  # This will cause the load to be skipped when filtered in __start_filling_db_cycle

        # Convert coordinates to WKT format
        pickup_points = WKTElement(
            f'POINT({pickup_coordinates[0]} {pickup_coordinates[1]})') if pickup_coordinates else None
        delivery_points = WKTElement(
            f'POINT({delivery_coordinates[0]} {delivery_coordinates[1]})') if delivery_coordinates else None

        coordinates_note = f"Pickup coordinates: {pickup_coordinates}, Delivery coordinates: {delivery_coordinates}"
        instructions = load.get('additionalInfo', '')
        combined_notes = f"{instructions}\n{coordinates_note}"
        # Extract broker name from shipper info if available
        brokerage = load.get('shipper', {}).get(
            'companyName', 'Central Dispatch')
        # Calculate total weight from vehicles
        total_weight = 0
        for vehicle in load.get('vehicles', []):
            if vehicle and vehicle.get('shippingSpecs') and vehicle.get('shippingSpecs').get('weight'):
                total_weight += vehicle.get('shippingSpecs').get('weight', 0)

        load_model_instance = LoadModel(
            external_load_id=str(load.get('id', '')),
            brokerage=brokerage,
            pickup_location=pickup_location,
            delivery_location=delivery_location,
            pickup_points=pickup_points,
            delivery_points=delivery_points,
            price=str(load['price']['total']),
            milage=float(load.get('distance', 0)),
            is_operational=not load.get('hasInOpVehicle', False),
            contact_phone=load['shipper'].get('phone', ''),
            notes=combined_notes,
            loadboard_source="central_dispatch",
            created_at=load.get('createdDate', ''),
            date_ready=load.get('availableDate', ''),
            n_vehicles=len(load.get('vehicles', [])),
            weight=float(total_weight)
        )

        return load_model_instance

    def fetch_db_loads(self, state):
        print(f"Fetching existing loads from the database for state: {state}...")
        if self.__db_Session is None:
            print("Database session is not initialized.")
            return []

        # Filter loads where pickup_location contains the state code
        # Example: "ABBEVILLE, AL 36310" for state="AL"
        existing_loads = self.__db_Session.query(
            LoadModel.external_load_id,
            LoadModel.price,
            LoadModel.milage,
            LoadModel.pickup_location,
            LoadModel.delivery_location
        ).filter(
            LoadModel.pickup_location.contains(f", {state} ")
        ).all()

        # Convert query results to dictionaries with proper keys
        existing_loads_dicts = [
            {
                'external_load_id': row[0],
                'price': row[1],
                'milage': row[2],
                'pickup_location': row[3],
                'delivery_location': row[4]
            }
            for row in existing_loads
        ]

        return existing_loads_dicts

    def save_loads_to_db(self, non_duplicate_loads):
        print("Saving non-duplicate filtered loads to the database...")
        if len(non_duplicate_loads) == 0:
            print("No new loads to process, every load is already in the database")
            return

        if len(non_duplicate_loads) > 0:
            load_model_instances = [
                model for model in (self.__format_and_get_load_model(load) for load in non_duplicate_loads)
                if model is not None  # Filter out None values that result from KeyError
            ]

            # Only proceed if there are valid models to save
            if load_model_instances and self.__db_Session is not None:
                self.__db_Session.bulk_save_objects(load_model_instances)
                self.__db_Session.commit()
                time.sleep(15)
                print(
                    f"Inserted {len(load_model_instances)} loads into DB")
                print("--------------------------------------------------------------------")
                print("\n")
            else:
                print("No valid loads to insert into DB")