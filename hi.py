import requests
import pandas as pd
import re
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

# Function to clean HTML content
def clean_html(html_content):
    text = re.sub(r'<[^>]+>', '', html_content)
    text = re.sub(r'\n+', '\n', text).strip()
    text = re.sub(r'•', '- ', text)
    return text

# New function for reverse geocoding with geopy
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
            full_address = location.address

            return {
                'Address': full_address,
                'City': city,
                'State': state,
                'Country': country,
                'Postal Code': postal_code,
                'Lat': lat,
                'Long': lon
            }
        else:
            return {
                'Address': 'Location Not Found',
                'City': 'N/A',
                'State': 'N/A',
                'Country': 'N/A',
                'Postal Code': 'N/A',
                'Lat': lat,
                'Long': lon
            }
    except GeocoderTimedOut:
        print("Geocoding service timed out. Please try again.")
        return {
            'Address': 'Location Not Found',
            'City': 'N/A',
            'State': 'N/A',
            'Country': 'N/A',
            'Postal Code': 'N/A',
            'Lat': lat,
            'Long': lon
        }
    except Exception as e:
        print(f"An error occurred: {e}")
        return {
            'Address': 'Location Not Found',
            'City': 'N/A',
            'State': 'N/A',
            'Country': 'N/A',
            'Postal Code': 'N/A',
            'Lat': lat,
            'Long': lon
        }

# Set the API URL
api_url = "https://www.courseseeker.edu.au/search-engine/courses/course/_search"

# Parameters for the request
size = 50  # Number of results per request
start_from = 10000  # Start from 10000 to fetch additional courses

# Request to get the additional courses
response = requests.get(api_url, params={"size": size, "from": start_from})

if response.status_code == 200 and response.headers['Content-Type'].startswith('application/json'):
    api_response = response.json()
    hits = api_response['hits']['hits']  # This is the list of course details
    
    course_data = []  # To store all course details

    # Process each course in the additional batch
    for course in hits:
        try:
            course_id = course.get('_id', 'N/A')
            title = course.get('_source', {}).get('name', 'N/A')
            institution_name = course.get('_source', {}).get('institutionName', 'N/A')
            level_of_qualification = course.get('_source', {}).get('levelOfQualificationDesc', 'N/A')
            study_area = course.get('_source', {}).get('studyArea', 'N/A')
            course_overview = clean_html(course.get('_source', {}).get('description', 'N/A'))

            # Assuming we get latitude and longitude from campuses
            campuses = course.get('_source', {}).get('campuses', [])
            if campuses:
                latitude = campuses[0].get('geolocation', {}).get('lat', None)
                longitude = campuses[0].get('geolocation', {}).get('lon', None)

                if latitude is not None and longitude is not None:
                    location_details = get_location_details(latitude, longitude)
                else:
                    location_details = {
                        'Address': 'Location Not Available',
                        'City': 'N/A',
                        'State': 'N/A',
                        'Country': 'N/A',
                        'Postal Code': 'N/A',
                        'Lat': latitude,
                        'Long': longitude
                    }
            else:
                location_details = {
                    'Address': 'Location Not Available',
                    'City': 'N/A',
                    'State': 'N/A',
                    'Country': 'N/A',
                    'Postal Code': 'N/A',
                    'Lat': None,
                    'Long': None
                }

            # Store the course data
            course_data.append({
                "Title": title,
                "Institution Name": institution_name,
                "Level of Qualification": level_of_qualification,
                "Study Area": study_area,
                "Course Overview": course_overview,
                "Address": location_details['Address'],
                "City": location_details['City'],
                "State": location_details['State'],
                "Country": location_details['Country'],
                "Postal Code": location_details['Postal Code'],
                "Lat": location_details['Lat'],
                "Long": location_details['Long'],
            })
            print(f"Retrieved Course - Title: {title}, Institution: {institution_name}")

        except Exception as e:
            print(f"Error extracting course details for course ID {course_id}: {e}")

    # Convert the course data into a DataFrame
    df = pd.DataFrame(course_data)

    # Save the data to a CSV file
    df.to_csv("additional_courses.csv", index=False)

    print("Scraping completed. Data saved to additional_courses.csv")
else:
    raise ValueError(f"Failed to retrieve additional courses: {response.status_code} {response.text}")
