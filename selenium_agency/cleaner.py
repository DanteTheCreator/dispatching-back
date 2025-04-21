from resources.models import LoadModel, get_db
from datetime import datetime, timedelta
from sqlalchemy import delete
import time


class Cleaner:
    def __init__(self):
        self.__db_Session = next(get_db())

    def __start_cleaning_cycle(self, in_between_delay=1):
        # Get yesterday's date
        yesterday = datetime.now().date() - timedelta(days=1)
        
        # Create delete statement for loads from yesterday
        delete_stmt = delete(LoadModel).where(LoadModel.created_at < yesterday)
        
        try:
            # Execute the delete statement
            self.__db_Session.execute(delete_stmt)
            self.__db_Session.commit()
            print(f"Successfully deleted loads from {yesterday}")
        except Exception as e:
            self.__db_Session.rollback()
            print(f"Error deleting loads: {str(e)}")
        finally:
            self.__db_Session.close()

    def run(self):
        while True:
            self.__start_cleaning_cycle(in_between_delay=1)
            # Sleep for 24 hours before next cleaning cycle
            time.sleep(24 * 60 * 60)