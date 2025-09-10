from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Float, Integer, String, DateTime, Boolean, JSON, func, ForeignKey, UniqueConstraint, Enum, text
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION, ARRAY
from datetime import datetime
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine, Column, Integer, String, DateTime, VARCHAR, Numeric
from geoalchemy2 import Geometry
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
import psycopg2

# # SQLAlchemy Setup
#DATABASE_URL = "postgresql://postgres:dispatchingisprofitable@/dispatcher-bot-db?host=/var/run/postgresql"
DATABASE_URL = "postgresql://postgres:dispatchingisprofitable@localhost:5432/postgres"

# Create engine with improved connection pooling and timeout settings
engine = create_engine(
    DATABASE_URL,
    pool_size=5,  # Reduced pool size to prevent connection exhaustion
    max_overflow=10,  # Reduced overflow to prevent too many connections
    pool_timeout=20,  # Reduced timeout to fail faster
    pool_recycle=1800,  # Recycle connections every 30 minutes (reduced from 1 hour)
    pool_pre_ping=True,  # Test connections before use
    echo=False,  # Disable SQL logging to reduce overhead
    connect_args={
        "connect_timeout": 15,  # Increased connection timeout
        "options": "-c statement_timeout=30000",  # 30 second statement timeout
        "application_name": "dispatching_api"  # Add application name for monitoring
    }
)

Base = declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        # Test the connection with a simple query
        db.execute(text("SELECT 1"))
        yield db
    except (SQLAlchemyError, psycopg2.Error) as e:
        print(f"Database connection error: {e}")
        try:
            db.rollback()
        except Exception as rollback_error:
            print(f"Error during rollback: {rollback_error}")
        raise HTTPException(
            status_code=500,
            detail="Database connection failed"
        )
    finally:
        try:
            db.close()
        except Exception as e:
            print(f"Error closing database connection: {e}")


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
    saved_by = Column(ARRAY(Integer))
    enclosed_trailer = Column(Boolean)

   
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
   max_milage = Column(Float)
   desired_destination = Column(VARCHAR(100))

class RouteModel(Base):
    __tablename__ = "routes"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    driver_id = Column(Integer, nullable=False)
    loads = Column(JSON, nullable=False)
    milage = Column(Float, nullable=False)
    total_rpm = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    status = Column(Enum('Pending', 'Approved', 'Rejected', name='status_type'), default='Pending')

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
    partner_brokers = Column(ARRAY(VARCHAR(100)), nullable=True)
    blacklist_brokers = Column(ARRAY(VARCHAR(100)), nullable=True)
     
class ZipCodeDatabase(Base):
    __tablename__ = "zip_code_database"
    
    zip = Column(String(5), primary_key=True, nullable=False)
    type = Column(String(20), nullable=True)
    primary_city = Column(String(100), nullable=True)
    state = Column(String(2), nullable=True)
    county = Column(String(50), nullable=True)
    timezone = Column(String(50), nullable=True)
    area_codes = Column(String(200), nullable=True)
    latitude = Column(Numeric(8, 2), nullable=True)
    longitude = Column(Numeric(8, 2), nullable=True)
    irs_estimated_population = Column(Integer, nullable=True)
    
    def __repr__(self):
        return f"<ZipCode(zip='{self.zip}', city='{self.primary_city}', state='{self.state}')>"