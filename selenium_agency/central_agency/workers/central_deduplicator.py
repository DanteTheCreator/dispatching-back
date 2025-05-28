from utils.array_deduplicator import ArrayDeduplicator
from .central_data_worker import CentralDataWorker

class CentralDeduplicatorWorker(CentralDataWorker):
    def __init__(self):
        self.__array_deduplicator = ArrayDeduplicator() 
    
    def deduplicate_loads(self, target_loads, db_loads):
        print(f"Deduplicating {len(target_loads)} target loads against {len(db_loads)} database loads.")
        deduplicated_loads = self.__array_deduplicator.apply_deduplication(target=target_loads, 
                                                                           based_on=db_loads, 
                                                                           target_id_keyword='id', 
                                                                           base_id_keyword='external_load_id', 
                                                                           attributes_compare_callback=self.attributes_compare_callback)
        return deduplicated_loads
