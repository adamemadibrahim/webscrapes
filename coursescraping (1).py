from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import requests
import re
import time

# Set up WebDriver
driver = webdriver.Chrome()

# Open the course search page
url = "https://www.courseseeker.edu.au/courses"
driver.get(url)

# Wait for the course items to load
wait = WebDriverWait(driver, 20)
wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "course-item")))  # Adjust class name if necessary

time.sleep(2)  # Allow additional time for all content to load

# Helper function to extract value safely from dictionaries
def safe_extract(data, keys, default='N/A'):
    for key in keys:
        if isinstance(data, dict) and key in data:
            data = data[key]
        else:
            return default
    return data

# Function to clean HTML content using string manipulation
def clean_html(html_content):
    text = re.sub(r'<[^>]+>', '', html_content)
    text = re.sub(r'\n+', '\n', text).strip()
    text = re.sub(r'•', '- ', text)
    return text

# Function for reverse geocoding
def reverse_geocode(lat, lon, api_key):
    geocode_url = f"https://api.opencagedata.com/geocode/v1/json?q={lat}+{lon}&key={api_key}"
    response = requests.get(geocode_url)
    if response.status_code == 200:
        results = response.json()
        if results['results']:
            return results['results'][0]['formatted']
    return 'Location Not Found'

# Set your OpenCage API key here
api_key = '51c6206982d4438d9d6391b28e23fe95'

# Extract all courses from the API with pagination
api_url = "https://www.courseseeker.edu.au/search-engine/courses/course/_search"
course_data = []  # To store all course details
size = 50  # Number of results per request
from_ = 0  # Starting point for pagination

# Loop until 50 courses are retrieved
while True:
    response = requests.get(api_url, params={"size": size, "from": from_})

    if response.status_code == 200 and response.headers['Content-Type'].startswith('application/json'):
        api_response = response.json()
        total_courses = api_response['hits']['total']
        hits = api_response['hits']['hits']  # This is the list of course details
        
        # Process each course in the current batch
        for course in hits:
            try:
                # Extract _id and name for each course
                course_id = safe_extract(course, ['_id'], 'N/A')
                title = safe_extract(course, ['_source', 'name'], 'N/A')  # Ensure we get the name

                # Construct the correct API URL using the course ID
                course_details_url = f"https://www.courseseeker.edu.au/search-engine/courses/course/{course_id}"
                course_response = requests.get(course_details_url)

                if course_response.status_code == 200 and course_response.headers['Content-Type'].startswith('application/json'):
                    course_json = course_response.json()
                else:
                    raise ValueError(f"Invalid API response for course {course_id}: {course_response.status_code} {course_response.text}")

                source = course_json.get('_source', {})

                # Extract new fields
                institution_name = safe_extract(source, ['institutionName'], 'N/A')
                level_of_qualification = safe_extract(source, ['levelOfQualificationDesc'], 'N/A')
                study_area = safe_extract(source, ['studyArea'], 'N/A')
                course_overview = clean_html(safe_extract(source, ['description'], 'N/A'))

                # Extract Admissions Criteria as Yuzee Prerequisites
                admissions_criteria = safe_extract(source, ['features'], default=[])
                if isinstance(admissions_criteria, list) and len(admissions_criteria) > 0:
                    cleaned_criteria = clean_html(admissions_criteria[0]['value'])
                else:
                    cleaned_criteria = 'N/A'

                # Extract ATAR data
                atar_profile = source.get('atarProfile', {})
                highest_atar = safe_extract(atar_profile, ['highestAtarUnadjusted'], 'N/A')
                median_atar = safe_extract(atar_profile, ['medianAtarUnadjusted'], 'N/A')
                lowest_atar = safe_extract(atar_profile, ['lowestAtarUnadjusted'], 'N/A')

                # Delivery Mode
                attendance_modes = safe_extract(source, ['attendanceModes'], default='')
                attendance_modes_list = attendance_modes.split(',') if isinstance(attendance_modes, str) else []
                delivery_mode_1 = attendance_modes_list[0] if len(attendance_modes_list) > 0 else 'N/A'
                delivery_mode_2 = attendance_modes_list[1] if len(attendance_modes_list) > 1 else 'N/A'

                # Duration
                full_time_duration = f"{safe_extract(source, ['fullTime'], 'N/A')} years"
                part_time_duration = safe_extract(source, ['partTime'], 'N/A')

                # Course Code
                course_code = safe_extract(source, ['courseCodeTac'])

                # Extract Career Opportunities if "CAREER-OPP" code exists
                career_opportunities = next(
                    (clean_html(item['value']) for item in source.get('features', []) if item.get('code') == "CAREER-OPP"), 
                    'N/A'
                )

                # Extract Geolocation
                geolocation = safe_extract(source, ['geolocation'], {})
                latitude = safe_extract(geolocation, ['lat'], 'N/A')
                longitude = safe_extract(geolocation, ['lon'], 'N/A')

                # Get location from reverse geocoding
                formatted_location = 'Location Not Available'
                if latitude != 'N/A' and longitude != 'N/A':
                    formatted_location = reverse_geocode(latitude, longitude, api_key)

                # Format Location with Geolocation
                campuses = safe_extract(source, ['campuses'], [])
                locations = []
                for campus in campuses:
                    campus_name = campus.get('campusName', 'N/A')
                    campus_state = campus.get('state', 'N/A')
                    locations.append(f"{campus_name}, {campus_state}")
                location = '; '.join(locations) + f" ({formatted_location})"

                # Practical Experience
                practical_experience = "Practical Experience"

                # Fees and Charges
                fees = safe_extract(source, ['fees'])
                fees_link = safe_extract(source, ['tacLink'])

                # Store the course data
                course_data.append({
                    "Title": title,  # This now correctly adds the course name
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
                    "Location": location
                })
                print(f"Retrieved Course - Title: {title}, Institution: {institution_name}, Level: {level_of_qualification}")

            except Exception as e:
                print(f"Error extracting course details for course ID {course_id}: {e}")

        # Break the loop if we've retrieved 50 courses
        print(f"Retrieved {len(hits)} courses, Total so far: {len(course_data)}")
        if len(course_data) == len(course_data["hits"]):
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

print("Scraping completed. Data saved to test_courses.csv")
