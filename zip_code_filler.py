import csv
from typing import List, Dict, Optional
from resources.models import get_db
from sqlalchemy import Column, String, Boolean, Integer, Float, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert

Base = declarative_base()

class ZipCodeDatabase(Base):
    __tablename__ = 'zip_code_database'
    
    zip = Column(String(5), primary_key=True)
    type = Column(String(20))
    primary_city = Column(String(100))
    state = Column(String(2))
    county = Column(String(100))
    timezone = Column(String(100))
    area_codes = Column(String(100))
    latitude = Column(Float)
    longitude = Column(Float)
    irs_estimated_population = Column(Integer)

db_Session = next(get_db())

def safe_truncate(value: str, max_length: int) -> str:
    """Safely truncate string to maximum length."""
    if value is None:
        return None
    return value[:max_length] if len(value) > max_length else value

def read_zip_code_data(csv_file_path: str) -> List[Dict]:
    """
    Read ZIP code data from CSV file and return as list of dictionaries.
    
    Args:
        csv_file_path: Path to the ZIP code CSV file
        
    Returns:
        List of dictionaries containing ZIP code data
    """
    zip_codes = []
    
    with open(csv_file_path, 'r', encoding='utf-8') as file:
        # Skip the comment line at the beginning
        first_line = file.readline()
        if first_line.startswith('//'):
            # Reset to beginning and skip comment line
            file.seek(0)
            file.readline()
        else:
            # Reset to beginning if no comment
            file.seek(0)
            
        reader = csv.DictReader(file)
        
        for row in reader:
            try:
                # Clean and convert data types with safe truncation
                zip_data = {
                    'zip': safe_truncate(row['zip'].strip(), 5),
                    'type': safe_truncate(row['type'].strip(), 20),
                    'primary_city': safe_truncate(row['primary_city'].strip(), 100) if row['primary_city'].strip() else None,
                    'state': safe_truncate(row['state'].strip(), 2) if row['state'].strip() else None,
                    'county': safe_truncate(row['county'].strip(), 100) if row['county'].strip() else None,
                    'timezone': safe_truncate(row['timezone'].strip(), 100) if row['timezone'].strip() else None,
                    'area_codes': safe_truncate(row['area_codes'].strip(), 100) if row['area_codes'].strip() else None,
                    'latitude': float(row['latitude']) if row['latitude'].strip() else None,
                    'longitude': float(row['longitude']) if row['longitude'].strip() else None,
                    'irs_estimated_population': int(row['irs_estimated_population']) if row['irs_estimated_population'].strip() else 0
                }
                
                zip_codes.append(zip_data)
                
            except (ValueError, TypeError) as e:
                print(f"Skipping invalid row for ZIP {row.get('zip', 'unknown')}: {e}")
                continue
    
    return zip_codes

def insert_zip_codes_to_db(session: Session, zip_codes: List[Dict]) -> int:
    """
    Insert ZIP code data into the database using UPSERT (INSERT ON CONFLICT).
    
    Args:
        session: SQLAlchemy database session
        zip_codes: List of ZIP code dictionaries
        
    Returns:
        Number of records processed
    """
    processed_count = 0
    failed_count = 0
    batch_size = 100  # Reduced batch size for better error isolation
    
    try:
        for i in range(0, len(zip_codes), batch_size):
            batch = zip_codes[i:i + batch_size]
            
            try:
                # Use PostgreSQL's INSERT ... ON CONFLICT ... DO UPDATE
                stmt = insert(ZipCodeDatabase).values(batch)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['zip'],
                    set_=dict(
                        type=stmt.excluded.type,
                        primary_city=stmt.excluded.primary_city,
                        state=stmt.excluded.state,
                        county=stmt.excluded.county,
                        timezone=stmt.excluded.timezone,
                        area_codes=stmt.excluded.area_codes,
                        latitude=stmt.excluded.latitude,
                        longitude=stmt.excluded.longitude,
                        irs_estimated_population=stmt.excluded.irs_estimated_population
                    )
                )
                
                session.execute(stmt)
                session.commit()
                processed_count += len(batch)
                print(f"Processed batch {i//batch_size + 1}: {len(batch)} records")
                
            except Exception as batch_error:
                session.rollback()
                print(f"Batch {i//batch_size + 1} failed: {batch_error}")
                
                # Try to process records individually to identify problematic ones
                for j, single_record in enumerate(batch):
                    try:
                        stmt = insert(ZipCodeDatabase).values([single_record])
                        stmt = stmt.on_conflict_do_update(
                            index_elements=['zip'],
                            set_=dict(
                                type=stmt.excluded.type,
                                primary_city=stmt.excluded.primary_city,
                                state=stmt.excluded.state,
                                county=stmt.excluded.county,
                                timezone=stmt.excluded.timezone,
                                area_codes=stmt.excluded.area_codes,
                                latitude=stmt.excluded.latitude,
                                longitude=stmt.excluded.longitude,
                                irs_estimated_population=stmt.excluded.irs_estimated_population
                            )
                        )
                        
                        session.execute(stmt)
                        session.commit()
                        processed_count += 1
                        
                    except Exception as single_error:
                        session.rollback()
                        failed_count += 1
                        print(f"Failed to insert ZIP {single_record.get('zip', 'unknown')}: {single_error}")
                        
                        # Log the problematic record for debugging
                        print(f"Problematic record: {single_record}")
                        continue
            
    except Exception as e:
        session.rollback()
        print(f"Critical error inserting ZIP codes: {e}")
        raise
    
    print(f"Processing complete: {processed_count} successful, {failed_count} failed")
    return processed_count

def fill_zip_code_database():
    """
    Main function to read CSV and populate the database.
    """
    csv_file_path = 'zip_code_database.csv'
    
    try:
        # Read ZIP codes from CSV
        print("Reading ZIP code data from CSV...")
        zip_codes = read_zip_code_data(csv_file_path)
        print(f"Read {len(zip_codes)} ZIP codes from CSV")
        
        # Insert into database
        print("Inserting ZIP codes into database...")
        processed_count = insert_zip_codes_to_db(db_Session, zip_codes)
        print(f"Successfully processed {processed_count} ZIP codes in database")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db_Session.close()

# Example usage:
if __name__ == "__main__":
    fill_zip_code_database()