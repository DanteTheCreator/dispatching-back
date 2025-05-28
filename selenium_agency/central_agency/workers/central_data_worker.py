
class CentralDataWorker:
    def __init__(self):
        pass 

    def __format_location(self, location_data, get_recursive):
        """Helper method to format location string from location data"""
        city = get_recursive(location_data, 'city')
        state = get_recursive(location_data, 'state')
        zip_code = get_recursive(location_data, 'zip')
        result = f"{city}, {state} {zip_code}".lower()
        return result
    
    def __is_mileage_similar(self, base_mileage, target_mileage, tolerance=0.02):
        """Check if target mileage is within tolerance range of base mileage"""
        return base_mileage * (1 - tolerance) <= target_mileage <= base_mileage * (1 + tolerance)
    
    def attributes_compare_callback(self, target, base, get_recursive):
        """Compare load attributes to determine if they represent the same load"""
        # Extract price and mileage for comparison
        target_price = get_recursive(target, 'price')["total"]
        base_price = get_recursive(base, 'price')
        target_mileage = get_recursive(target, 'distance')
        base_mileage = get_recursive(base, 'milage')
        
        # Format target pickup and delivery locations
        target_origin = get_recursive(target, 'origin')
        target_destination = get_recursive(target, 'destination')
        target_pickup_location = self.__format_location(target_origin, get_recursive)
        target_delivery_location = self.__format_location(target_destination, get_recursive)
        
        # Get base locations
        base_pickup_location = get_recursive(base, 'pickup_location')
        base_delivery_location = get_recursive(base, 'delivery_location')
        
        # Compare all relevant attributes
        return (target_price == base_price and
                target_pickup_location == base_pickup_location and
                target_delivery_location == base_delivery_location and
                self.__is_mileage_similar(base_mileage, target_mileage))

    