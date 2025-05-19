from . import utils
from .utils import get_recursive

class ArrayDeduplicator:

  def __init__(self):
      pass
  
  def _objects_equal(self, target_object, 
                           base_object, 
                           attributes_compare_callback,
                           target_id_keyword=None, 
                           base_id_keyword=None):
    # Convert objects to dictionaries
    target_dict = target_object if isinstance(target_object, dict) else vars(target_object) if hasattr(target_object, '__dict__') else {'value': target_object}
    base_dict = base_object if isinstance(base_object, dict) else vars(base_object) if hasattr(base_object, '__dict__') else {'value': base_object}

    # If ID keywords are provided, compare only those attributes
    if target_id_keyword and base_id_keyword:
        target_id = target_dict.get(target_id_keyword)
        base_id = base_dict.get(base_id_keyword)
        if target_id is not None and base_id is not None:
            if str(target_id) == str(base_id):
                return True
    attributes_compare_callback_result = attributes_compare_callback(target_object, base_object, get_recursive)
    return attributes_compare_callback_result

  def _filter_items(self, target, based_on_items, target_id_keyword, base_id_keyword, attributes_compare_callback):
    result = []
    counter = 1
    for item in target:
        print(f"Deduplicating load: {counter} /  {len(target)}")
        counter += 1
        exists_in_based_on = False
        for base_item in based_on_items:
            if self._objects_equal(item, base_item, attributes_compare_callback, target_id_keyword, base_id_keyword):
                exists_in_based_on = True
                break

        if not exists_in_based_on:
            result.append(item)

    return result

  def apply_deduplication(self, target, based_on, target_id_keyword, base_id_keyword, attributes_compare_callback=None):
      if not target:
          print("Warning: 'to' array is empty. Returning an empty array.")
          return []

      if not based_on:
          print("Warning: 'based_on' array is empty. Returning a copy of 'to' array.")
          return target.copy()

      # Use comparison-based filtering which works with any input types
      return self._filter_items(target, based_on, target_id_keyword, base_id_keyword, attributes_compare_callback)