def get_recursive(data, key):
    """
    Recursively search through a nested dictionary to find the first 
    occurrence of a key and return its value.

    Args:
        data: Dictionary or list to search through
        key: Key to search for

    Returns:
        Value of the first matching key found, or None if key not found
    """
    if isinstance(data, dict):
        # Check if the key exists at current level
        if key in data:
            return data[key]

        # If not found, search in all values that are dicts or lists
        for value in data.values():
            if isinstance(value, (dict, list)):
                result = get_recursive(value, key)
                if result is not None:
                    return result

    elif isinstance(data, list):
        # Search through list items that are dicts or lists
        for item in data:
            if isinstance(item, (dict, list)):
                result = get_recursive(item, key)
                if result is not None:
                    return result

    # Key not found in this branch
    return None

def objects_equal(target_object, 
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