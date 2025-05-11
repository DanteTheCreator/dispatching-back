class ArrayDeduplicator:

  def __init__(self):
      pass

  def _objects_equal(self, target_object, base_object, target_id_keyword, base_id_keyword):

    if target_id_keyword is None or base_id_keyword is None:
        #compare all attributes
        item1_attrs = {attr_name: attr_value for attr_name, attr_value in vars(target_object).items() if not attr_name.startswith('_')}
        item2_attrs = {attr_name: attr_value for attr_name, attr_value in vars(base_object).items() if not attr_name.startswith('_')}
        return item1_attrs == item2_attrs
    
    

    if (hasattr(target_object, target_id_keyword) and hasattr(base_object, base_id_keyword)):
        if (getattr(target_object, target_id_keyword) == getattr(base_object, base_id_keyword)):
            return True
        else:
            # compare rest of the attributes except the unique_id_keyword
            item1_attrs = {attr_name: attr_value for attr_name, attr_value in vars(target_object).items() if not attr_name.startswith('_') and attr_name != unique_id_keyword}
            item2_attrs = {attr_name: attr_value for attr_name, attr_value in vars(target_object).items() if not attr_name.startswith('_') and attr_name != unique_id_keyword}

            # Making union of both dictionaries
            all_keys = set(item1_attrs.keys()).intersection(set(item2_attrs.keys()))

            attrs_match = True

            # if values of union keys are same in both dictionaries then return True
            for key in all_keys:
                if key in item1_attrs and key in item2_attrs:
                    if item1_attrs[key] != item2_attrs[key]:
                        attrs_match = False
                        break

            return attrs_match
    else:
        print(f"Warning: {target_id_keyword} or {base_id_keyword} not found in one of the objects.")
        return False

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

    
  def _filter_items(self, target, based_on_items, target_id_keyword, base_id_keyword):
    if target_id_keyword and base_id_keyword:
        result = []
        for item in target:
            exists_in_based_on = False
            for base_item in based_on_items:
                if self._objects_equal(item, base_item, target_id_keyword, base_id_keyword):
                    exists_in_based_on = True
                    break
            
            if not exists_in_based_on:
                result.append(item)

    else:
        result = [item for item in based_on_items if not any(self._compare_items(item, base_item) for base_item in based_on_items)]
            
    return result

  def apply_deduplication(self, target, based_on, target_id_keyword, base_id_keyword):
      if not target:
          print("Warning: 'to' array is empty. Returning an empty array.")
          return []

      if not based_on:
          print("Warning: 'based_on' array is empty. Returning a copy of 'to' array.")
          return target.copy()
      
      # Use comparison-based filtering which works with any input types
      return self._filter_items(target, based_on, target_id_keyword, base_id_keyword)