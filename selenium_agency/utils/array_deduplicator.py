from . import utils
from .utils import get_recursive

class ArrayDeduplicator:

  def __init__(self):
      pass

  def _objects_equal(self, target_object, 
                           base_object, 
                           target_id_keyword=None, 
                           base_id_keyword=None, 
                           attributes_compare_callback):
    # Convert objects to dictionaries
    target_dict = target_object if isinstance(target_object, dict) else vars(target_object) if hasattr(target_object, '__dict__') else {'value': target_object}
    base_dict = base_object if isinstance(base_object, dict) else vars(base_object) if hasattr(base_object, '__dict__') else {'value': base_object}

    # If ID keywords are provided, compare only those attributes
    if target_id_keyword and base_id_keyword:
        target_id = target_dict.get(target_id_keyword)
        base_id = base_dict.get(base_id_keyword)
        if target_id is not None and base_id is not None:
            return str(target_id) == str(base_id)
        return False
    
    # Otherwise, compare the entire dictionaries
    attributes_compare_callback_result = attributes_compare_callback(target_object, base_object, get_recursive)
    return target_dict == base_dict

  def deduplicate(self, array):

      if not array:
          return []

      return self._deduplicate_unhashable(array)

  def _deduplicate_unhashable(self, array):
      result = []

      for item in array:
          is_duplicate = False
          for existing_item in result:
              if self._objects_equal(item, existing_item):
                  is_duplicate = True
                  break
          if not is_duplicate:
              result.append(item)

      return result


  def _filter_items(self, target, based_on_items, target_id_keyword, base_id_keyword, attributes_compare_callback):
    """
    Filter items from target that don't exist in based_on_items.

    Args:
        target: List of target items to filter
        based_on_items: List of base items to compare against
        target_id_keyword: ID attribute/key name in target items
        base_id_keyword: ID attribute/key name in base items

    Returns:
        List of items from target that don't exist in based_on_items
    """
    result = []
    for item in target:
        exists_in_based_on = False
        for base_item in based_on_items:
            if self._objects_equal(item, base_item, target_id_keyword, base_id_keyword, attributes_compare_callback):
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