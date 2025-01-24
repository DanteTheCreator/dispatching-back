from sqlalchemy.orm import sessionmaker, Session
from fastapi import FastAPI, Query, Security, HTTPException, Depends
from fastapi.security import APIKeyHeader
from http import HTTPStatus
import os
from typing import List
from models import RouteModel, LoadModel, Dispatcher, DriverModel, get_db
from fastapi.middleware.cors import CORSMiddleware
from faker import Faker


fake = Faker()

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
API_KEY = os.getenv("API_KEY", "your-secret-api-key")  # Default value for testing

async def get_api_key(api_key: str = Security(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail="Invalid API Key"
        )
    return api_key


@app.get("/get_profile/{dispatcher_id}", dependencies=[Depends(get_api_key)])
def get_profile(dispatcher_id: str, db: Session = Depends(get_db)):
    dispatcher = db.query(Dispatcher).filter(Dispatcher.id == dispatcher_id).first()
    if dispatcher is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Dispatcher not found")
    return dispatcher

# Endpoint to fetch all loads
@app.get("/all_loads", dependencies=[Depends(get_api_key)])
def get_all_loads():
    return {'status':'hello'}

@app.get("/get_all_drivers/{dispatcher_id}", dependencies=[Depends(get_api_key)])
def get_all_drivers(dispatcher_id: str, db: Session = Depends(get_db)):
    dispatcher = db.query(Dispatcher).filter(Dispatcher.id == dispatcher_id).first()
    if dispatcher is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Dispatcher not found")
    
    driver_ids = dispatcher.drivers
    if not isinstance(driver_ids, list):
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Dispatcher drivers data is invalid or empty"
        )
    # Query for drivers using the fetched driver_ids
    drivers = db.query(DriverModel).filter(DriverModel.driver_id.in_(driver_ids)).all()
    if not drivers:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Drivers not found"
        )
    return drivers

@app.get("/get_active_drivers/{dispatcher_id}", dependencies=[Depends(get_api_key)])
def get_active_drivers(dispatcher_id: str, db: Session = Depends(get_db)):
    dispatcher = db.query(Dispatcher).filter(Dispatcher.id == dispatcher_id).first()
    if dispatcher is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Dispatcher not found")
    
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
    driver = db.query(DriverModel).filter(DriverModel.driver_id == driver_id).first()
    if driver is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Driver not found")
    
    # Get the scalar value from the query
    current_active_status = db.query(DriverModel.active).filter(DriverModel.driver_id == driver_id).scalar()
    
    db.query(DriverModel).filter(DriverModel.driver_id == driver_id).update(
        {"active": not current_active_status}
    )
    db.commit()
    
    # Refresh the driver instance to get the updated value
    db.refresh(driver)
    return {"driver":driver}


@app.get("/get_routes/{driver_id}", dependencies=[Depends(get_api_key)])
def get_routes(driver_id: str, db: Session = Depends(get_db)):
    routes = db.query(RouteModel).filter(RouteModel.driver_id == driver_id).all()
    if not routes:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="No routes found for this driver"
        )

    for route in routes:
        if route.loads: #type: ignore
            first_load = db.query(LoadModel).filter(LoadModel.load_id == route.loads[0]).first()
            last_load = db.query(LoadModel).filter(LoadModel.load_id == route.loads[-1]).first()
            if first_load and last_load:
                route.pick = first_load.pickup_location
                route.dest = last_load.delivery_location
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
    
    return {"loads": db_loads}


@app.patch("/update_driver/{driver_id}", dependencies=[Depends(get_api_key)])
def update_driver(driver_id: str, driver_data: dict, db: Session = Depends(get_db)):
    driver = db.query(DriverModel).filter(DriverModel.driver_id == driver_id).first()
    if driver is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Driver not found")
    
    for key, value in driver_data.items():
        if hasattr(driver, key):
            setattr(driver, key, value)
    
    db.commit()
    db.refresh(driver)
    return driver

@app.post("/approve_route/{route_id}", dependencies=[Depends(get_api_key)])
def approve_route(route_id: str, db: Session = Depends(get_db)):
    route = db.query(RouteModel).filter(RouteModel.route_id == route_id).first()
    if route is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Route not found")
    
    driver_id = route.driver_id

    # Move the route to confirmed routes
    confirmed_route = RouteModel(
        route_id=route.route_id,
        driver_id=route.driver_id,
        loads=route.loads,
        milage=route.milage,
        total_rpm=route.total_rpm,
        total_price=route.total_price,
        created_at=route.created_at
    )
    db.add(confirmed_route)

    # Delete all other routes associated with the driver
    db.query(RouteModel).filter(RouteModel.driver_id == driver_id, RouteModel.route_id != route_id).delete()

    db.commit()
    return {"message": "Route approved and other routes deleted"}

@app.delete("/reject_route/{route_id}", dependencies=[Depends(get_api_key)])
def reject_route(route_id: str, db: Session = Depends(get_db)):
    route = db.query(RouteModel).filter(RouteModel.route_id == route_id).first()
    if route is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Route not found")
    
    db.delete(route)
    db.commit()
    return {"message": "Route rejected and deleted"}

# Endpoint to fetch all loads
@app.get("/health")
def activate_driver(db: Session = Depends()):
    return 'Hello World'


# Create tables if not exists (optional)
# Base.metadata.create_all(bind=engine)
