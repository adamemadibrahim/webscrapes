from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import requests
import re
import time
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

# Set up WebDriver
driver = webdriver.Chrome()

# Open the course search page
url = "https://www.courseseeker.edu.au/courses"
driver.get(url)

# Wait for the course items to load
wait = WebDriverWait(driver, 20)
wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "course-item")))

time.sleep(2)  # Allow additional time for all content to load

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

# Extract all courses from the API with pagination
api_url = "https://www.courseseeker.edu.au/search-engine/courses/course/_search"
course_data = []  # To store all course details
size = 50  # Number of results per request
from_ = 0  # Starting point for pagination

# Loop until we reach the desired number of courses
while True:
    response = requests.get(api_url, params={"size": size, "from": from_})

    if response.status_code == 200 and response.headers['Content-Type'].startswith('application/json'):
        api_response = response.json()
        hits = api_response['hits']['hits']  # This is the list of course details
        
        # Process each course in the current batch
        for course in hits:
            try:
                # Extract _id and name for each course
                course_id = course.get('_id', 'N/A')
                title = course.get('_source', {}).get('name', 'N/A')

                # Construct the correct API URL using the course ID
                course_details_url = f"https://www.courseseeker.edu.au/search-engine/courses/course/{course_id}"
                course_response = requests.get(course_details_url)

                if course_response.status_code == 200 and course_response.headers['Content-Type'].startswith('application/json'):
                    course_json = course_response.json()
                else:
                    raise ValueError(f"Invalid API response for course {course_id}: {course_response.status_code} {course_response.text}")

                source = course_json.get('_source', {})

                # Extract relevant fields
                institution_name = source.get('institutionName', 'N/A')
                level_of_qualification = source.get('levelOfQualificationDesc', 'N/A')
                study_area = source.get('studyArea', 'N/A')
                course_overview = clean_html(source.get('description', 'N/A'))

                # Extract Admissions Criteria as Yuzee Prerequisites
                admissions_criteria = source.get('features', [])
                if admissions_criteria and isinstance(admissions_criteria, list):
                    cleaned_criteria = clean_html(admissions_criteria[0].get('value', 'N/A'))
                else:
                    cleaned_criteria = 'N/A'

                # Extract ATAR data
                atar_profile = source.get('atarProfile', {})
                highest_atar = atar_profile.get('highestAtarUnadjusted', 'N/A')
                median_atar = atar_profile.get('medianAtarUnadjusted', 'N/A')
                lowest_atar = atar_profile.get('lowestAtarUnadjusted', 'N/A')

                # Delivery Mode
                attendance_modes = source.get('attendanceModes', '')
                attendance_modes_list = attendance_modes.split(',') if attendance_modes else []
                delivery_mode_1 = attendance_modes_list[0] if len(attendance_modes_list) > 0 else 'N/A'
                delivery_mode_2 = attendance_modes_list[1] if len(attendance_modes_list) > 1 else 'N/A'

                # Duration
                full_time_duration = f"{source.get('fullTime', 'N/A')} years"
                part_time_duration = source.get('partTime', 'N/A')

                # Course Code
                course_code = source.get('courseCodeTac')

                # Extract Career Opportunities if "CAREER-OPP" code exists
                career_opportunities = next(
                    (clean_html(item['value']) for item in source.get('features', []) if item.get('code') == "CAREER-OPP"), 
                    'N/A'
                )

                # Extract Geolocation from campuses
                campuses = source.get('campuses', [])
                if campuses and isinstance(campuses, list):
                    # Assuming we take the first campus for geolocation
                    first_campus = campuses[0]
                    latitude = first_campus.get('geolocation', {}).get('lat')
                    longitude = first_campus.get('geolocation', {}).get('lon')
                else:
                    latitude = None
                    longitude = None

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

                # Practical Experience
                practical_experience = "Practical Experience"

                # Fees and Charges
                fees = source.get('fees')
                fees_link = source.get('tacLink')

                # Store the course data
                course_data.append({
                    "Title": title,
                    "Institution Name": institution_name,
                    "Level of Qualification": level_of_qualification,
                    "Study Area": study_area,
                    "Course Overview": course_overview,
                    "Yuzee Prerequisites": cleaned_criteria,
                    "ATAR Highest": highest_atar,
                    "ATAR Median": median_atar,
                    "ATAR Lowest": lowest_atar,
                    "Delivery Mode 1": delivery_mode_1,
                    "Delivery Mode 2": delivery_mode_2,
                    "Full Time Duration": full_time_duration,
                    "Part Time Duration": part_time_duration,
                    "Course Code": course_code,
                    "Career Outcome": career_opportunities if career_opportunities != 'N/A' else '',
                    "Practical Experience": practical_experience,
                    "Fees Link": fees_link,
                    "Address": location_details['Address'],
                    "City": location_details['City'],
                    "State": location_details['State'],
                    "Country": location_details['Country'],
                    "Postal Code": location_details['Postal Code'],
                    "Lat": location_details['Lat'],
                    "Long": location_details['Long'],
                    "Institution Location": {  # Adding the Institution Location as an object
                        "address": location_details['Address'],
                        "city": location_details['City'],
                        "state": location_details['State'],
                        "country": location_details['Country'],
                        "lat": latitude,
                        "long": longitude,
                        "postal_code": location_details['Postal Code']
                    }
                })
                print(f"Retrieved Course - Title: {title}, Institution: {institution_name}, Level: {level_of_qualification}")
                if len(course_data) == 1:
                    break

            except Exception as e:
                print(f"Error extracting course details for course ID {course_id}: {e}")

        # Break the loop if we've retrieved enough courses
        print(f"Retrieved {len(hits)} courses, Total so far: {len(course_data)}")
        if len(course_data) == 1:
            break
        
        from_ += size  # Move to the next batch of courses
    else:
        raise ValueError(f"Failed to retrieve courses: {response.status_code} {response.text}")

# Convert the course data into a DataFrame
df = pd.DataFrame(course_data)

# Modify Delivery Mode in the DataFrame after appending data
df['Delivery Mode 1'] = df['Delivery Mode 1'].replace({'I': 'Classroom Based', 'E': 'Online'})
df['Delivery Mode 2'] = df['Delivery Mode 2'].replace({'I': 'Classroom Based', 'E': 'Online'})

# Save the data to a CSV file
df.to_csv("courses.csv", index=False)

# Close the WebDriver
driver.quit()

print("Scraping completed. Data saved to courses.csv")
