from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Float, Integer, String, DateTime, Boolean, JSON, func, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, DOUBLE_PRECISION, ARRAY
import uuid
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine, Column, Integer, String, DateTime, VARCHAR
from geoalchemy2 import Geometry

# # SQLAlchemy Setup
#DATABASE_URL = "postgresql://postgres:dispatchingisprofitable@/dispatcher-bot-db?host=/var/run/postgresql"
DATABASE_URL = "postgresql://postgres:dispatchingisprofitable@rothschildrentals.pro:5432/dispatcher-bot-db"
engine = create_engine(DATABASE_URL)

Base = declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# # Define your model (adjust fields as needed)
class LoadModel(Base):
    __tablename__ = "loads"
    
    load_id = Column(Integer, primary_key=True, server_default="nextval('loads_load_id_seq'::regclass)")
    external_load_id = Column(String(50))
    brokerage = Column(String(100))
    pickup_location = Column(String)
    delivery_location = Column(String)
    pickup_points = Column(Geometry('POINT'))
    delivery_points = Column(Geometry('POINT'))
    price = Column(Float)
    milage = Column(DOUBLE_PRECISION)
    is_operational = Column(Boolean)
    contact_phone = Column(String(25))
    notes = Column(String)
    loadboard_source = Column(String(50))
    created_at = Column(DateTime)
    date_ready = Column(DateTime)
    n_vehicles = Column(Integer)
    weight = Column(Float)
    is_saved = Column(Boolean, default=False)
    saved_by = Column(ARRAY(Integer))

   
class Dispatcher(Base):
    __tablename__ = "dispatchers"
    
    id = Column(Integer, primary_key=True, server_default="nextval('dispatchers_id_seq'::regclass)")
    name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False)
    phone = Column(String(25), nullable=False)
    role = Column(String(50), nullable=False)
    drivers = Column(ARRAY(Integer), nullable=True)
    profile_picture = Column(String, nullable=True)
    password = Column(VARCHAR(255), nullable=False)
    
class DriverModel(Base):
   __tablename__ = "drivers"

   driver_id = Column(Integer, primary_key=True)
   trailer_size = Column(Integer)
   desired_gross = Column(DOUBLE_PRECISION)
   desired_rpm = Column(DOUBLE_PRECISION) 
   active = Column(Boolean)
   full_name = Column(String(50))
   phone = Column(String(15))
   states = Column(ARRAY(String(2)))
   location = Column(String(100))

class RouteModel(Base):
    __tablename__ = "routes"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    driver_id = Column(Integer, nullable=False)
    loads = Column(JSON, nullable=False)
    milage = Column(Float, nullable=False)
    total_rpm = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    

class ConfirmedRouteModel(Base):
   __tablename__ = "confirmed_routes"
   
   id = Column(Integer, primary_key=True, autoincrement=True)
   driver_id = Column(Integer, nullable=False)
   loads = Column(JSON, nullable=False)
   milage = Column(Float, nullable=False)
   total_rpm = Column(Float, nullable=False)
   total_price = Column(Float, nullable=False)
   created_at = Column(DateTime, server_default=func.now())
   
class CompanyModel(Base):
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False)
    phone = Column(String(25), nullable=False)
    address = Column(String, nullable=False)
    mc_number = Column(String(50), nullable=False)
    dot_number = Column(String(50), nullable=False)
    company_logo = Column(String, nullable=False)