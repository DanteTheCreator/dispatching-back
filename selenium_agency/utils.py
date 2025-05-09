class ArrayDeduplicator:

  def __init__(self):
      pass

  def _get_value(self, obj, key):
      """Helper method to get a value from an object or dictionary."""
      if isinstance(obj, dict):
          return obj.get(key)
      else:
          return getattr(obj, key) if hasattr(obj, key) else None

  def _objects_equal(self, obj1, obj2, unique_id_keywords=None):

    if unique_id_keywords is None:
        #compare all attributes
        if isinstance(obj1, dict) and isinstance(obj2, dict):
            return obj1 == obj2
        
        item1_attrs = {attr_name: attr_value for attr_name, attr_value in vars(obj1).items() if not attr_name.startswith('_')}
        item2_attrs = {attr_name: attr_value for attr_name, attr_value in vars(obj2).items() if not attr_name.startswith('_')}
        return item1_attrs == item2_attrs

    
    if (self._get_value(obj1, unique_id_keywords[0]) == self._get_value(obj2, unique_id_keywords[1])) or (self._get_value(obj1, unique_id_keywords[1]) == self._get_value(obj2, unique_id_keywords[0])):
        #print("success")
        return True
    else:
        #print("compare rest of the attributes")
        # compare rest of the attributes except the unique_id_keywords
        if isinstance(obj1, dict) and isinstance(obj2, dict):
            item1_attrs = {k: v for k, v in obj1.items() if k not in unique_id_keywords}
            item2_attrs = {k: v for k, v in obj2.items() if k not in unique_id_keywords}
        else:
            item1_attrs = {attr_name: attr_value for attr_name, attr_value in vars(obj1).items() 
                          if not attr_name.startswith('_') and attr_name not in unique_id_keywords}
            item2_attrs = {attr_name: attr_value for attr_name, attr_value in vars(obj2).items() 
                          if not attr_name.startswith('_') and attr_name not in unique_id_keywords}

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

    
  def _filter_items(self, to_items, based_on_items, is_in_base_array_callback):
    
    result = []
    for item in to_items:
        exists_in_based_on = False
        for base_item in based_on_items:
            if is_in_base_array_callback(item, base_item):
                exists_in_based_on = True
                break
            # if self._objects_equal(item, base_item, unique_id_keywords):
            #     exists_in_based_on = True
            #     break
        
        if not exists_in_based_on:
            result.append(item)

    return result

  def apply_deduplication(self, to, based_on, is_in_base_array_callback):
      if not to:
          print("Warning: 'to' array is empty. Returning an empty array.")
          return []

      if not based_on:
          print("Warning: 'based_on' array is empty. Returning a copy of 'to' array.")
          return to.copy()
      
      # Use comparison-based filtering which works with any input types
      return self._filter_items(to, based_on, is_in_base_array_callback)