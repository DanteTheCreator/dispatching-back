from geoalchemy2.elements import WKTElement
import time
from resources.models import LoadModel, get_db
from .central_data_worker import CentralDataWorker
from selenium_agency.utils.utils import objects_equal
from sqlalchemy.exc import OperationalError, DisconnectionError
import logging

class CentralDbWorker(CentralDataWorker):
    def __init__(self):
        self.__db_Session = None
        self._init_db_session()
    
    def _init_db_session(self):
        """Initialize or reinitialize the database session"""
        try:
            if self.__db_Session:
                self.__db_Session.close()
            self.__db_Session = next(get_db())
        except Exception as e:
            logging.error(f"Failed to initialize database session: {e}")
            self.__db_Session = None
    
    def _execute_with_retry(self, operation, max_retries=3, retry_delay=5):
        """Execute a database operation with retry logic for connection issues"""
        for attempt in range(max_retries):
            try:
                return operation()
            except (OperationalError, DisconnectionError) as e:
                logging.warning(f"Database connection error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    print(f"Database connection lost. Retrying in {retry_delay} seconds... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                    self._init_db_session()  # Reinitialize the session
                    if self.__db_Session is None:
                        continue
                else:
                    print(f"Database connection failed after {max_retries} attempts")
                    raise
            except Exception as e:
                logging.error(f"Unexpected database error: {e}")
                raise

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
            weight=float(total_weight)        )

        return load_model_instance

    def fetch_db_loads(self, state):
        print(f"Fetching existing loads from the database for state: {state}...")
        if self.__db_Session is None:
            print("Database session is not initialized.")
            self._init_db_session()
            if self.__db_Session is None:
                print("Failed to initialize database session.")
                return []

        def fetch_loads():
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
            return existing_loads

        try:
            existing_loads = self._execute_with_retry(fetch_loads)
        except Exception as e:
            print(f"Failed to fetch loads after retries: {e}")
            return []

        # Convert query results to dictionaries with proper keys
        existing_loads_dicts = [
            {
                'external_load_id': row[0],
                'price': row[1],
                'milage': row[2],
                'pickup_location': row[3],
                'delivery_location': row[4]
            }
            for row in existing_loads        ]

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
                def save_loads():
                    self.__db_Session.bulk_save_objects(load_model_instances)
                    self.__db_Session.commit()
                    return len(load_model_instances)

                try:
                    saved_count = self._execute_with_retry(save_loads)
                    time.sleep(15)
                    print(f"Inserted {saved_count} loads into DB")
                    print("--------------------------------------------------------------------")
                    print("\n")
                except Exception as e:
                    print(f"Failed to save loads to database: {e}")
                    # Try to rollback the transaction
                    try:
                        self.__db_Session.rollback()
                    except:
                        pass
            else:
                print("No valid loads to insert into DB")

    def sanitize_db(self, remote_loads, state):
        print("Sanitizing database...")
        if self.__db_Session is None:
            print("Database session is not initialized.")
            self._init_db_session()
            if self.__db_Session is None:
                print("Failed to initialize database session. Skipping sanitization.")
                return

        def fetch_existing_loads():
            return self.__db_Session.query(LoadModel).filter(
                LoadModel.pickup_location.contains(f", {state} ")
            ).all()

        # Fetch all existing loads for the specified state with retry logic
        try:
            existing_db_loads = self._execute_with_retry(fetch_existing_loads)
        except Exception as e:
            print(f"Failed to fetch existing loads after retries: {e}")
            return

        print(f"Found {len(existing_db_loads)} existing loads in DB for state {state}")
        print(f"Comparing against {len(remote_loads)} remote loads")

        # Find database loads that don't exist in remote data
        loads_to_delete = []
        counter = 1
        for db_load in existing_db_loads:
            print(f"\rSanitizing db load: {counter} / {len(existing_db_loads)}", end='', flush=True)
            counter += 1
            found_match = False
            for remote_load in remote_loads:
                if objects_equal(
                    target_object=remote_load,
                    base_object=db_load,
                    attributes_compare_callback=self.attributes_compare_callback,
                    target_id_keyword='id',
                    base_id_keyword='external_load_id'
                ):
                    found_match = True
                    break
            
            if not found_match:
                loads_to_delete.append(db_load)

        # Delete loads that weren't found in remote data
        if loads_to_delete:
            def delete_loads():
                counter = 1
                for load in loads_to_delete:
                    print(f"\rDeleting obsolete load: {counter} / {len(loads_to_delete)}", end='', flush=True)
                    counter += 1
                    self.__db_Session.delete(load)
                self.__db_Session.commit()
                return len(loads_to_delete)

            try:
                deleted_count = self._execute_with_retry(delete_loads)
                print(f"Deleted {deleted_count} obsolete loads from DB for state {state}")
            except Exception as e:
                print(f"Failed to delete obsolete loads: {e}")
                # Try to rollback the transaction
                try:
                    self.__db_Session.rollback()
                except:
                    pass
        else:
            print(f"No obsolete loads found for state {state}")

    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensure database session is properly closed"""
        if self.__db_Session:
            try:
                if exc_type:
                    self.__db_Session.rollback()
                self.__db_Session.close()
            except Exception as e:
                logging.error(f"Error closing database session: {e}")
            finally:
                self.__db_Session = None