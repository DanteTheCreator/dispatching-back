from central_interactor import CentralInteractor
from workers.central_db_worker import CentralDbWorker
from workers.central_deduplicator import CentralDeduplicatorWorker
from workers.central_token_worker import CentralTokenWorker
import sys
import os
# Append the project root directory to sys.path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from selenium_agency.api.central_api_client import CentralAPIClient
from selenium_agency.cache.central_cache import CentralCacheService
from selenium_driver import SeleniumDriver


class CentralConfigurator:
    def __init__(self):
        self.__selenium_driver = SeleniumDriver()
        self.__api_client = CentralAPIClient()
        self.__cache_service = CentralCacheService()
        self.__db_worker = CentralDbWorker()
        self.__deduplicator_worker = CentralDeduplicatorWorker()
        self.__central_token_worker = CentralTokenWorker(driver=self.__driver,
                                                         cache_service=self.__cache_service)
        self.initialize_driver()
        
    def initialize_driver(self):
        self.__selenium_driver.initialize_driver()
        self.__driver = self.__selenium_driver.get_driver()
        
    def get_driver(self):
        if self.__selenium_driver is None:
            self.initialize_driver()
        return self.__driver

    def configured_central_interactor(self):
        # Implement the configuration logic here
        interactor = CentralInteractor(
            api_client=self.__api_client,
            deduplicator=self.__deduplicator_worker, 
            db_worker=self.__db_worker,
            token_worker=self.__central_token_worker
        )
        return interactor