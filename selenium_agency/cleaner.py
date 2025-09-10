from resources.models import LoadModel, get_db
from datetime import datetime, timedelta
from sqlalchemy import delete
import time


class Cleaner:
    def __init__(self):
        pass

    def __start_cleaning_cycle(self, in_between_delay=1):
        db_session = next(get_db())
        try:
            # Get yesterday's date
            yesterday = datetime.now().date() - timedelta(days=1)
            
            # Create delete statement for loads from yesterday
            delete_stmt = delete(LoadModel).where(LoadModel.created_at < yesterday)
            
            # Execute the delete statement
            db_session.execute(delete_stmt)
            db_session.commit()
            print(f"Successfully deleted loads from {yesterday}")
        except Exception as e:
            db_session.rollback()
            print(f"Error deleting loads: {str(e)}")
        finally:
            db_session.close()

    def run(self):
        while True:
            self.__start_cleaning_cycle(in_between_delay=1)
            # Sleep for 24 hours before next cleaning cycle
            time.sleep(24 * 60 * 60)