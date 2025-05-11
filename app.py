from sqlalchemy import text
from sqlalchemy.orm import Session
from fastapi import FastAPI, Query, Security, HTTPException, Depends
from fastapi.security import APIKeyHeader
from http import HTTPStatus
import os
from typing import List, Optional
from datetime import datetime
from resources.models import RouteModel, LoadModel, SavedLoadModel,Dispatcher, DriverModel, get_db, ConfirmedRouteModel, CompanyModel
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


# FastAPI App
app = FastAPI(title="Dispatching API",
              description="An API for interacting with Dispatching DBs",
              version="0.1.0",
              root_path="/api")

# Define allowed origins
origins = [
    "http://localhost:5173",  # Frontend development server
    "https://rothschildrentals.pro",  # Backend production domain
]

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all HTTP headers
)

api_key_header = APIKeyHeader(name="X-API-Key")
# Default value for testing
API_KEY = os.getenv("API_KEY", "your-secret-api-key")


async def get_api_key(api_key: str = Security(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail="Invalid API Key"
        )
    return api_key

class LoginRequest(BaseModel):
    email: str
    password: str


@app.post("/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(Dispatcher).filter(Dispatcher.email ==
                                       request.email, Dispatcher.password == request.password).first()
    if user is None:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED,
                            detail="Invalid username or password")

    # Generate a token (for simplicity, using the API key as a token here)
    token = API_KEY
    return {"token": token, "dispatcher_id": user.id}


@app.get("/get_profile/{dispatcher_id}", dependencies=[Depends(get_api_key)])
def get_profile(dispatcher_id: str, db: Session = Depends(get_db)):
    dispatcher = db.query(Dispatcher).filter(
        Dispatcher.id == dispatcher_id).first()
    if dispatcher is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND,
                            detail="Dispatcher not found")
    return dispatcher



@app.get("/all_loads", dependencies=[Depends(get_api_key)])
def get_all_loads():
    return {'status': 'hello'}


@app.get("/get_all_drivers/{dispatcher_id}", dependencies=[Depends(get_api_key)])
def get_all_drivers(dispatcher_id: str, db: Session = Depends(get_db)):
    dispatcher = db.query(Dispatcher).filter(
        Dispatcher.id == dispatcher_id).first()
    if dispatcher is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND,
                            detail="Dispatcher not found")

    driver_ids = dispatcher.drivers
    if not isinstance(driver_ids, list):
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Dispatcher drivers data is invalid or empty"
        )
    # Query for drivers using the fetched driver_ids
    drivers = db.query(DriverModel).filter(
        DriverModel.driver_id.in_(driver_ids)).all()
    if not drivers:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Drivers not found"
        )
    return drivers


@app.get("/get_active_drivers/{dispatcher_id}", dependencies=[Depends(get_api_key)])
def get_active_drivers(dispatcher_id: str, db: Session = Depends(get_db)):
    dispatcher = db.query(Dispatcher).filter(
        Dispatcher.id == dispatcher_id).first()
    if dispatcher is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND,
                            detail="Dispatcher not found")

    driver_ids = dispatcher.drivers
    if not isinstance(driver_ids, list):
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Dispatcher drivers data is invalid or empty"
        )

    # Query for active drivers using the fetched driver_ids
    active_drivers = db.query(DriverModel).filter(
        DriverModel.driver_id.in_(driver_ids),
        DriverModel.active == True
    ).all()

    if not active_drivers:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Active drivers not found"
        )
    return active_drivers


@app.post("/toggle_driver_activity/{driver_id}", dependencies=[Depends(get_api_key)])
def toggle_activity(driver_id: str, db: Session = Depends(get_db)):
    driver = db.query(DriverModel).filter(
        DriverModel.driver_id == driver_id).first()
    if driver is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND,
                            detail="Driver not found")

    # Get the scalar value from the query
    current_active_status = db.query(DriverModel.active).filter(
        DriverModel.driver_id == driver_id).scalar()

    db.query(DriverModel).filter(DriverModel.driver_id == driver_id).update(
        {"active": not current_active_status}
    )
    db.commit()

    # Refresh the driver instance to get the updated value
    db.refresh(driver)
    return {"driver": driver}


@app.get("/get_routes/{driver_id}", dependencies=[Depends(get_api_key)])
def get_routes(driver_id: str, db: Session = Depends(get_db)):
    routes = db.query(RouteModel).filter(
        RouteModel.driver_id == driver_id).all()
    if not routes:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="No routes found for this driver"
        )

    for route in routes:
        loads = getattr(route, 'loads', [])
        first_load = db.query(LoadModel).filter(
            LoadModel.load_id == loads[0]).first()
        last_load = db.query(LoadModel).filter(
            LoadModel.load_id == loads[-1]).first()
        if first_load and last_load:
            route.pick = first_load.pickup_location.split(" ")[-2]
            route.dest = last_load.delivery_location.split(" ")[-2]
    return routes


@app.get("/get_loads_and_glink_for_route", dependencies=[Depends(get_api_key)])
def get_loads_and_glink_for_route(loads: List[str] = Query(None), db: Session = Depends(get_db)):
    if not loads:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Loads list is required"
        )

    # Query the database for loads using the load IDs
    db_loads = db.query(LoadModel).filter(LoadModel.load_id.in_(loads)).all()

    if not db_loads:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="No loads found with the provided IDs"
        )

    # Construct the Google Maps route link
    base_url = "https://www.google.com/maps/dir/"
    locations = []
    
    # Convert SQLAlchemy models to dictionaries
    loads_data = []
    
    for load in db_loads:
        locations.append(load.pickup_location)
        locations.append(load.delivery_location)
        
        # Convert SQLAlchemy model to dict with additional fields
        load_dict = {
            "load_id": load.load_id,
            "pickup_location": load.pickup_location,
            "delivery_location": load.delivery_location,
            "milage": load.milage,
            "price": load.price,
            "notes": load.notes,
            "contact_phone": load.contact_phone,
            "brokerage": load.brokerage,
            "loadboard_source": load.loadboard_source,
            "is_operational": load.is_operational
        }
        loads_data.append(load_dict)

    google_maps_link = base_url + "/".join(locations)

    return {"loads": loads_data, "google_maps_link": google_maps_link}


@app.put("/update_driver", dependencies=[Depends(get_api_key)])
def update_driver(driver_data: dict, db: Session = Depends(get_db)):
    driver = db.query(DriverModel).filter(
        DriverModel.driver_id == driver_data['driver_id']).first()
    if driver is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND,
                            detail="Driver not found")

    for key, value in driver_data.items():
        if hasattr(driver, key):
            setattr(driver, key, value)

    db.commit()
    db.refresh(driver)
    return driver


@app.post("/approve_route/{route_id}", dependencies=[Depends(get_api_key)])
def approve_route(route_id: str, db: Session = Depends(get_db)):
    route = db.query(RouteModel).filter(RouteModel.id == route_id).first()
    if route is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND,
                            detail="Route not found")

    driver_id = route.driver_id

    # Move the route to confirmed routes
    confirmed_route = ConfirmedRouteModel(
        id=route.id,
        driver_id=route.driver_id,
        loads=route.loads,
        milage=route.milage,
        total_rpm=route.total_rpm,
        total_price=route.total_price,
        created_at=route.created_at
    )
    db.add(confirmed_route)

    # Delete all other routes associated with the driver
    db.query(RouteModel).filter(RouteModel.driver_id == driver_id).delete()
    db.query(DriverModel).filter(DriverModel.driver_id ==
                                 driver_id).update({"active": False})
    db.commit()
    return {"message": "Route approved and other routes deleted"}


@app.delete("/reject_route/{route_id}", dependencies=[Depends(get_api_key)])
def reject_route(route_id: str, db: Session = Depends(get_db)):
    route = db.query(RouteModel).filter(RouteModel.id == route_id).first()
    if route is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND,
                            detail="Route not found")

    db.delete(route)
    db.commit()
    return {"message": "Route rejected and deleted"}


@app.get("/get_company/{company_id}", dependencies=[Depends(get_api_key)])
def get_company_info(company_id: str, db: Session = Depends(get_db)):
    company = db.query(CompanyModel).filter(
        CompanyModel.id == company_id).first()
    if company is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND,
                            detail="Company not found")
    return company


@app.get("/health")
def health(db: Session = Depends(get_db)):
    return 'Hello World'


@app.get("/filter_loads", dependencies=[Depends(get_api_key)])
def filter_loads(
   n_vehicles: Optional[int] = None,
   min_price: Optional[float] = None,
   date_ready: Optional[datetime] = None,
   max_price: Optional[float] = None,
   min_milage: Optional[float] = None,
   max_milage: Optional[float] = None,
   brokerage: Optional[str] = None,
   min_weight: Optional[float] = None,
   max_weight: Optional[float] = None,
   origin: Optional[str] = None,
   destination: Optional[str] = None,
   db: Session = Depends(get_db)
):

    # Build the SQL query dynamically
    sql_query = """
        SELECT 
            load_id, external_load_id, brokerage, pickup_location, 
            delivery_location, price::float, milage, is_operational,
            contact_phone, notes, loadboard_source, created_at,
            date_ready, n_vehicles, weight
        FROM loads 
        WHERE 1=1
    """
    params = {}

    # Add filter conditions
    if min_price is not None:
        sql_query += " AND CAST(price AS FLOAT) >= :min_price"
        params['min_price'] = min_price
    if max_price is not None:
        sql_query += " AND CAST(price AS FLOAT) <= :max_price"
        params['max_price'] = max_price
    if min_milage is not None:
        sql_query += " AND milage >= :min_milage"
        params['min_milage'] = min_milage
    if max_milage is not None:
        sql_query += " AND milage <= :max_milage"
        params['max_milage'] = max_milage
    if brokerage:
        sql_query += " AND brokerage = :broker"
        params['broker'] = brokerage
    if min_weight is not None:
        sql_query += " AND weight >= :min_weight"
        params['min_weight'] = min_weight
    if max_weight is not None:
        sql_query += " AND weight <= :max_weight"
        params['max_weight'] = max_weight
    if origin:
        sql_query += " AND pickup_location ILIKE :origin"
        params['origin'] = f'%{origin}%'
    if destination:
        sql_query += " AND delivery_location ILIKE :destination"
        params['destination'] = f'%{destination}%'
    if n_vehicles is not None:
        sql_query += " AND n_vehicles = :n_vehicles"
        params['n_vehicles'] = n_vehicles
    if date_ready is not None:
        sql_query += " AND date_ready <= :date_ready"
        params['date_ready'] = date_ready
    sql_query += " ORDER BY created_at DESC"

    # Execute the raw SQL query
    result = db.execute(text(sql_query), params).all()
    if not result:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="No loads found matching the criteria"
        )

    # Convert rows to dictionaries and serialize datetime objects
    result = [dict(row._mapping) for row in result]
    for load_dict in result:
        for key, value in load_dict.items():
            if isinstance(value, datetime):
                load_dict[key] = value.isoformat()
    
    return result[0:25] 


@app.post("/save_load", dependencies=[Depends(get_api_key)])
def save_load(load_id: str, dispatcher_id: str, db: Session = Depends(get_db)):
    # Check if dispatcher exists
    dispatcher = db.query(Dispatcher).filter(Dispatcher.id == dispatcher_id).first()
    if not dispatcher:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Dispatcher not found"
        )

    # Check if load is already saved
    existing_saved_load = db.query(SavedLoadModel).filter(
        SavedLoadModel.load_id == load_id,
        SavedLoadModel.dispatcher_id == dispatcher_id
    ).first()

    if existing_saved_load:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Load is already saved"
        )

    # Get load data from loads table
    load_data = db.query(LoadModel).filter(LoadModel.load_id == load_id).first()
    if load_data is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Load not found"
        )
    
    # Create SavedLoadModel with all load data
    saved_load = SavedLoadModel(
        load_id=load_id,
        dispatcher_id=dispatcher_id,
        external_load_id=load_data.external_load_id,
        brokerage=load_data.brokerage,
        pickup_location=load_data.pickup_location,
        delivery_location=load_data.delivery_location,
        price=load_data.price,
        milage=load_data.milage,
        is_operational=load_data.is_operational,
        contact_phone=load_data.contact_phone,
        notes=load_data.notes,
        loadboard_source=load_data.loadboard_source,
        date_ready=load_data.date_ready,
        n_vehicles=load_data.n_vehicles,
        weight=load_data.weight
    )
    try:
        db.add(saved_load)
        db.commit()
        return {"message": "Load saved successfully"}
    except:
        db.rollback()
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=f"Failed to save load "
        )

@app.get("/get_saved_loads", dependencies=[Depends(get_api_key)])
def get_saved_loads(dispatcher_id: str, db: Session = Depends(get_db)):
    sql = """
    SELECT l.*
    FROM loads l
    JOIN saved_loads sl ON l.load_id = sl.load_id
    WHERE sl.dispatcher_id = :dispatcher_id
    ORDER BY l.created_at DESC
    """
    result = db.execute(text(sql), {"dispatcher_id": dispatcher_id}).all()
    
    if not result:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="No saved loads found"
        )

    # Convert rows to dictionaries and serialize datetime objects
    loads = [dict(row._mapping) for row in result]
    for load in loads:
        for key, value in load.items():
            if isinstance(value, datetime):
                load[key] = value.isoformat()
    
    return loads


@app.delete("/delete_saved_load", dependencies=[Depends(get_api_key)])
def delete_saved_load(load_id: str, dispatcher_id: str, db: Session = Depends(get_db)):
    saved_load = db.query(SavedLoadModel).filter(
        SavedLoadModel.load_id == load_id,
        SavedLoadModel.dispatcher_id == dispatcher_id
    ).first()
    
    if not saved_load:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Saved load not found"
        )

    try:
        db.delete(saved_load)
        db.commit()
        return {"message": "Load removed from saved loads"}
    except:
        db.rollback()
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Failed to delete saved load"
        )
        
@app.get("/is_saved", dependencies=[Depends(get_api_key)])
def is_saved(load_id: str, dispatcher_id: str, db: Session = Depends(get_db)):
    saved_load = db.query(SavedLoadModel).filter(
        SavedLoadModel.load_id == load_id,
        SavedLoadModel.dispatcher_id == dispatcher_id
    ).first()
    
    return {"is_saved": saved_load is not None}