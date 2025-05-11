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
