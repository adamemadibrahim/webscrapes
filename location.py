from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

def get_location_details(lat, lon):
    geolocator = Nominatim(user_agent="location_finder")

    try:
        location = geolocator.reverse((lat, lon), language='en', exactly_one=True)

        if location and 'address' in location.raw:
            address = location.raw['address']
            city = address.get('city', address.get('town', address.get('village', '')))
            state = address.get('state', '')
            country = address.get('country', '')
            postal_code = address.get('postcode', '')

            return {
                'City': city,
                'State': state,
                'Country': country,
                'Postal Code': postal_code,
                'Latitude': lat,
                'Longitude': lon
            }
        else:
            return None
    except GeocoderTimedOut:
        print("Geocoding service timed out. Please try again.")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

# Using the specified coordinates for the example
latitude = -37.80928600  # Example: Near Sydney
longitude = 144.96440900  # Example: Near Sydney

location_details = get_location_details(latitude, longitude)

if location_details:
    print(location_details)
else:
    print("Location details not found.")
