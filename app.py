from sqlalchemy import text
from sqlalchemy.orm import Session
from fastapi import FastAPI, Query, Security, HTTPException, Depends
from fastapi.security import APIKeyHeader
from http import HTTPStatus
import os
from typing import List, Optional
from datetime import datetime
from resources.models import RouteModel, LoadModel, Dispatcher, DriverModel, get_db, ConfirmedRouteModel, CompanyModel
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
            "is_operational": load.is_operational,
            "enclosed_trailer": load.enclosed_trailer,
            "created_at": load.created_at.isoformat(), 
            "saved_by": load.saved_by
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
    origin_region_id: Optional[int] = None,
    destination_region_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    # Base query parts
    select_clause = """
        SELECT DISTINCT
            l.load_id, l.external_load_id, l.brokerage, l.pickup_location, 
            l.delivery_location, l.price::float, l.milage, l.is_operational,
            l.contact_phone, l.notes, l.loadboard_source, l.created_at,
            l.date_ready, l.n_vehicles, l.weight, l.enclosed_trailer, l.saved_by
    """
    
    from_clause = "FROM loads l"
    joins = []
    where_conditions = []
    params = {}
    
    # Handle origin region filtering
    if origin_region_id is not None:
        from resources.models import Region
        origin_region = db.query(Region).filter(Region.id == origin_region_id).first()
        if not origin_region:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail="Origin region not found"
            )
        joins.append("""
            JOIN region_zip_codes rzc_origin ON 
            SUBSTRING(l.pickup_location FROM '[0-9]{5}') = rzc_origin.zip_code
        """)
        where_conditions.append("rzc_origin.region_id = :origin_region_id")
        params['origin_region_id'] = origin_region_id

    # Handle destination region filtering
    if destination_region_id is not None:
        from resources.models import Region
        dest_region = db.query(Region).filter(Region.id == destination_region_id).first()
        if not dest_region:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail="Destination region not found"
            )
        joins.append("""
            JOIN region_zip_codes rzc_dest ON 
            SUBSTRING(l.delivery_location FROM '[0-9]{5}') = rzc_dest.zip_code
        """)
        where_conditions.append("rzc_dest.region_id = :destination_region_id")
        params['destination_region_id'] = destination_region_id

    # Add all other filters
    if min_price is not None:
        where_conditions.append("CAST(l.price AS FLOAT) >= :min_price")
        params['min_price'] = min_price
    if max_price is not None:
        where_conditions.append("CAST(l.price AS FLOAT) <= :max_price")
        params['max_price'] = max_price
    if min_milage is not None:
        where_conditions.append("l.milage >= :min_milage")
        params['min_milage'] = min_milage
    if max_milage is not None:
        where_conditions.append("l.milage <= :max_milage")
        params['max_milage'] = max_milage
    if brokerage:
        where_conditions.append("l.brokerage = :broker")
        params['broker'] = brokerage
    if min_weight is not None:
        where_conditions.append("l.weight >= :min_weight")
        params['min_weight'] = min_weight
    if max_weight is not None:
        where_conditions.append("l.weight <= :max_weight")
        params['max_weight'] = max_weight
    if origin:
        where_conditions.append("l.pickup_location ILIKE :origin")
        params['origin'] = f'%{origin}%'
    if destination:
        where_conditions.append("l.delivery_location ILIKE :destination")
        params['destination'] = f'%{destination}%'
    if n_vehicles is not None:
        where_conditions.append("l.n_vehicles = :n_vehicles")
        params['n_vehicles'] = n_vehicles
    if date_ready is not None:
        where_conditions.append("l.date_ready <= :date_ready")
        params['date_ready'] = date_ready

    # Build final query
    sql_query = select_clause + " " + from_clause
    if joins:
        sql_query += " " + " ".join(joins)
    
    if where_conditions:
        sql_query += " WHERE " + " AND ".join(where_conditions)
    
    sql_query += " ORDER BY l.created_at DESC"

    # Execute query
    result = db.execute(text(sql_query), params).all()
    if not result:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="No loads found matching the criteria"
        )

    # Convert to response format
    loads_list = []
    for row in result:
        load_dict = {}
        for key, value in row._mapping.items():
            if isinstance(value, datetime):
                load_dict[key] = value.isoformat()
            else:
                load_dict[key] = value
        loads_list.append(load_dict)
    
    return loads_list[0:25]


@app.post("/save_load", dependencies=[Depends(get_api_key)])
def save_load(load_id: int, dispatcher_id: int, db: Session = Depends(get_db)):
    # Check if dispatcher exists
    dispatcher = db.query(Dispatcher).filter(Dispatcher.id == dispatcher_id).first()
    if not dispatcher:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Dispatcher not found"
        )

    # Get load data
    load = db.query(LoadModel).filter(LoadModel.load_id == load_id).first()
    if load is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Load not found"
        )

    # Check if already saved by this dispatcher
    saved_by_list = load.saved_by if load.saved_by is not None else []
    if dispatcher_id in saved_by_list:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Load is already saved"
        )

    try:
        # Update saved_by list and is_saved flag
        saved_by = load.saved_by or []
        saved_by.append(dispatcher_id)
        db.query(LoadModel).filter(LoadModel.load_id == load_id).update({
            "saved_by": saved_by
        })
        db.commit()
        return {"message": "Load saved successfully"}
    except:
        db.rollback()
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Failed to save load"
        )

@app.get("/get_saved_loads", dependencies=[Depends(get_api_key)])
def get_saved_loads(dispatcher_id: int, db: Session = Depends(get_db)):
    loads = db.query(LoadModel).filter(
        LoadModel.saved_by.contains([dispatcher_id])
    ).order_by(LoadModel.created_at.desc()).all()

    if not loads:
        raise HTTPException(
            status_code=HTTPStatus.NO_CONTENT,
            detail="No saved loads found"
        )
    
    # Convert SQLAlchemy models to dictionaries
    loads_data = []
    for load in loads:
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
            "is_operational": load.is_operational,
            "enclosed_trailer": load.enclosed_trailer,
            "created_at": load.created_at.isoformat(),
            "saved_by": load.saved_by
        }
        loads_data.append(load_dict)

    return {"loads": loads_data}

@app.delete("/delete_saved_load", dependencies=[Depends(get_api_key)])
def delete_saved_load(load_id: int, dispatcher_id: int, db: Session = Depends(get_db)):
    load = db.query(LoadModel).filter(LoadModel.load_id == load_id).first()
    if not load:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Load not found"
        )

    if load.saved_by is None or dispatcher_id not in load.saved_by:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Load is not saved by this dispatcher"
        )

    try:
        saved_by = load.saved_by.copy()
        saved_by.remove(dispatcher_id)
        db.query(LoadModel).filter(LoadModel.load_id == load_id).update({
            "saved_by": saved_by
        })
        db.commit()
        return {"message": "Load removed from saved loads"}
    except:
        db.rollback()
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, 
            detail="Failed to remove load"
        )

@app.get("/is_saved", dependencies=[Depends(get_api_key)])
def is_saved(load_id: str, dispatcher_id: str, db: Session = Depends(get_db)):
    load = db.query(LoadModel).filter(LoadModel.load_id == load_id).first()
    is_saved = load and load.saved_by and dispatcher_id in load.saved_by
    return {"is_saved": is_saved}


# Add to your existing FastAPI app

@app.get("/regions", dependencies=[Depends(get_api_key)])
def get_regions(db: Session = Depends(get_db)):
    """Get all regions for frontend dropdown"""
    from resources.models import Region
    
    regions = db.query(Region).order_by(Region.name).all()
    return [{"id": r.id, "name": r.name, "description": r.description} for r in regions]

    """Get all loads from a specific region (e.g., Long Island)"""
    from resources.models import Region, RegionZipCode
    
    # Verify region exists
    region = db.query(Region).filter(Region.id == region_id).first()
    if not region:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Region not found"
        )
    
    # Build dynamic SQL query similar to your filter_loads endpoint
    sql_query = """
        SELECT DISTINCT
            l.load_id, l.external_load_id, l.brokerage, l.pickup_location, 
            l.delivery_location, l.price::float, l.milage, l.is_operational,
            l.contact_phone, l.notes, l.loadboard_source, l.created_at,
            l.date_ready, l.n_vehicles, l.weight, l.enclosed_trailer, l.saved_by
        FROM loads l
        JOIN region_zip_codes rzc ON (
            SUBSTRING(l.pickup_location FROM '[0-9]{5}') = rzc.zip_code 
            OR SUBSTRING(l.delivery_location FROM '[0-9]{5}') = rzc.zip_code
        )
        WHERE rzc.region_id = :region_id
        ORDER BY l.created_at DESC
    """
    
    result = db.execute(text(sql_query), {"region_id": region_id}).all()
    
    if not result:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"No loads found for {region.name}"
        )
    
    # Convert to list of dictionaries (same as your filter_loads logic)
    loads_list = []
    for row in result:
        load_dict = {}
        for key, value in row._mapping.items():
            if isinstance(value, datetime):
                load_dict[key] = value.isoformat()
            else:
                load_dict[key] = value
        loads_list.append(load_dict)
    
    return {
        "region": {"id": region.id, "name": region.name},
        "loads": loads_list[:25],  # Limit like your other endpoint
        "total_found": len(loads_list)
    }