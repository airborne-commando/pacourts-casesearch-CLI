from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import os
import time
import random
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('case_search.log'),
        logging.StreamHandler()
    ]
)

ZIP_TO_COUNTY = {}
ZIP_TO_CITY = {}
DOCKET_TYPES = [
    "",  # Blank option
    "Civil",
    "Criminal",
    "Landlord/Tenant",
    "Miscellaneous",
    "Non-Traffic",
    "Summary Appeal",
    "Traffic"
]

def ensure_results_dir():
    os.makedirs('case_results', exist_ok=True)

def load_zip_mapping(zip_file='zip-database/zip-codes.txt'):
    try:
        with open(zip_file, 'r') as file:
            for line in file:
                if line.strip() and line.startswith("ZIP Code"):
                    parts = line.strip().split('\t')
                    if len(parts) >= 3:
                        zip_code = parts[0].replace("ZIP Code ", "").strip()
                        city = parts[1].strip().title()
                        county = parts[2].strip().upper()
                        ZIP_TO_COUNTY[zip_code] = county
                        ZIP_TO_CITY[zip_code] = city
        logging.info(f"Loaded ZIP code mapping with {len(ZIP_TO_COUNTY)} entries")
    except Exception as e:
        logging.error(f"Error loading ZIP code mapping: {e}")

def get_county(zip_code):
    return ZIP_TO_COUNTY.get(zip_code)

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    )
    
    service = Service(executable_path='/usr/bin/chromedriver')
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def read_input_from_file(file_path):
    data = []
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
            for line in lines:
                if line.startswith("zip") or line.startswith("ZIP") or not line.strip():
                    continue
                
                parts = line.strip().split('\t') if '\t' in line else line.strip().split(',')
                if len(parts) >= 3:
                    zip_code = parts[0].strip()
                    last_name = parts[1].strip()
                    first_name = parts[2].strip()
                    county = get_county(zip_code)
                    docket_type = parts[3].strip() if len(parts) > 3 else ""
                    
                    if county:
                        data.append({
                            'zip_code': zip_code,
                            'last_name': last_name,
                            'first_name': first_name,
                            'county': county,
                            'docket_type': docket_type
                        })
                    else:
                        logging.warning(f"No county found for ZIP {zip_code}: {line.strip()}")
    except Exception as e:
        logging.error(f"Error reading input file: {e}")
    return data

def search_participant(driver, last_name, first_name, county, docket_type="", retry_count=0):
    try:
        url = "https://ujsportal.pacourts.us/CaseSearch"
        driver.get(url)
        
        # Wait for the Search By dropdown
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#SearchBy-Control select"))
        )
        
        # Select Participant Name
        search_by_dropdown = Select(driver.find_element(By.CSS_SELECTOR, "#SearchBy-Control select"))
        search_by_dropdown.select_by_visible_text("Participant Name")
        
        # Wait for participant fields
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.NAME, "ParticipantLastName")))
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.NAME, "ParticipantFirstName")))
        
        driver.find_element(By.NAME, "ParticipantLastName").send_keys(last_name)
        driver.find_element(By.NAME, "ParticipantFirstName").send_keys(first_name)
        
        # Select county
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "#County-Control select"))
        )
        county_dropdown = Select(driver.find_element(By.CSS_SELECTOR, "#County-Control select"))
        try:
            county_dropdown.select_by_visible_text(county.title())
        except:
            if county.endswith(" COUNTY"):
                county_dropdown.select_by_visible_text(county.replace(" COUNTY", "").title())
            else:
                county_dropdown.select_by_visible_text(f"{county.title()} County")
        
        # Select docket type if specified
        if docket_type:
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "#DocketType-Control select"))
            )
            docket_dropdown = Select(driver.find_element(By.CSS_SELECTOR, "#DocketType-Control select"))
            try:
                docket_dropdown.select_by_visible_text(docket_type)
            except:
                logging.warning(f"Invalid docket type: {docket_type}")
        
        # Click Search
        search_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "btnSearch"))
        )
        search_button.click()
        
        # Wait for results
        try:
            WebDriverWait(driver, 15).until(
                lambda d: d.find_element(By.ID, "caseSearchResultGrid").is_displayed() or 
                         d.find_element(By.CLASS_NAME, "noResultsMessage").is_displayed()
            )
        except:
            pass
        
        # No results
        no_results = driver.find_elements(By.CLASS_NAME, "noResultsMessage")
        if no_results and "No results match" in no_results[0].text:
            return []
        
        # Parse table with URLs
        results = []
        try:
            table = driver.find_element(By.ID, "caseSearchResultGrid")
            rows = table.find_elements(By.TAG_NAME, "tr")[1:]
            for row in rows:
                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) >= 19:
                    docket_number = cols[2].text.strip()
                    case_caption = cols[4].text.strip()
                    case_status = cols[5].text.strip()
                    filing_date = cols[6].text.strip()
                    participant = cols[7].text.strip()
                    dob = cols[8].text.strip()
                    county_name = cols[9].text.strip()
                    docket_type_result = cols[10].text.strip()
                    
                    # Extract links but don't download them
                    links = cols[18].find_elements(By.TAG_NAME, "a")
                    docket_link = links[0].get_attribute("href") if len(links) > 0 else None
                    summary_link = links[1].get_attribute("href") if len(links) > 1 else None
                    
                    results.append({
                        'Docket Number': docket_number,
                        'Case Caption': case_caption,
                        'Case Status': case_status,
                        'Filing Date': filing_date,
                        'Participant': participant,
                        'Date of Birth': dob,
                        'County': county_name,
                        'Docket Type': docket_type_result,
                        'Search Name': f"{last_name}, {first_name}",
                        'Search County': county,
                        'Search Docket Type': docket_type,
                        'Docket PDF URL': docket_link,
                        'Summary PDF URL': summary_link
                    })
        except Exception as e:
            logging.warning(f"Error parsing results: {e}")
        
        return results
    
    except Exception as e:
        if retry_count < 2:
            delay = random.uniform(10, 30)
            logging.warning(f"Retry {retry_count+1} for {last_name}, {first_name} after error: {e}... Waiting {delay:.1f} sec...")
            time.sleep(delay)
            return search_participant(driver, last_name, first_name, county, docket_type, retry_count+1)
        else:
            logging.error(f"Max retries reached for {last_name}, {first_name} in {county}: {e}")
            return None

def save_results(results, last_name, first_name, county, docket_type=""):
    if not results:
        return None
    try:
        clean_last = "".join(c for c in last_name if c.isalnum())
        clean_first = "".join(c for c in first_name if c.isalnum())
        clean_county = "".join(c for c in county if c.isalnum())
        clean_docket = "".join(c for c in docket_type if c.isalnum()) if docket_type else "all"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        filename = f"case_results/{clean_last}_{clean_first}_{clean_county}_{clean_docket}_{timestamp}.csv"
        pd.DataFrame(results).to_csv(filename, index=False)
        logging.info(f"Saved CSV: {filename}")
        return filename
    except Exception as e:
        logging.error(f"Error saving results: {e}")
        return None

def process_search(driver, search_data):
    docket_type = search_data.get('docket_type', '')
    results = search_participant(driver, search_data['last_name'], search_data['first_name'], 
                               search_data['county'], docket_type)
    if results is None:
        return None
    elif not results:
        return save_results([{
            'Search Name': f"{search_data['last_name']}, {search_data['first_name']}",
            'Search County': search_data['county'],
            'Search Docket Type': docket_type,
            'Status': 'No results found'
        }], search_data['last_name'], search_data['first_name'], 
           search_data['county'], docket_type)
    else:
        return save_results(results, search_data['last_name'], search_data['first_name'], 
                          search_data['county'], docket_type)

def main():
    ensure_results_dir()
    load_zip_mapping()
    driver = setup_driver()
    
    try:
        print("\nPA Court Case Search")
        print("1. Search from file")
        print("2. Manual search")
        mode = input("Select option (1 or 2): ").strip()
        
        if mode == '1':
            file_path = input("Enter path to file: ").strip()
            search_data_list = read_input_from_file(file_path)
            for i, data in enumerate(search_data_list):
                if i > 0:
                    time.sleep(random.uniform(5, 15))
                process_search(driver, data)
        elif mode == '2':
            print("\nAvailable docket types:")
            for i, dtype in enumerate(DOCKET_TYPES[1:], 1):
                print(f"{i}. {dtype}")
            print("Leave blank for all types")
            
            while True:
                user_input = input("\nEnter search (zip,last,first[,docket_type]) or 'quit': ").strip()
                if user_input.lower() == 'quit':
                    break
                try:
                    parts = [x.strip() for x in user_input.split(',')]
                    zip_code = parts[0]
                    last = parts[1]
                    first = parts[2]
                    docket_type = parts[3] if len(parts) > 3 else ""
                    
                    # Convert numeric docket type to text if needed
                    if docket_type.isdigit():
                        try:
                            docket_type = DOCKET_TYPES[int(docket_type)]
                        except IndexError:
                            docket_type = ""
                    
                    county = get_county(zip_code)
                    if county:
                        process_search(driver, {
                            'zip_code': zip_code,
                            'last_name': last,
                            'first_name': first,
                            'county': county,
                            'docket_type': docket_type
                        })
                    else:
                        print(f"No county for ZIP {zip_code}")
                except ValueError:
                    print("Invalid format. Use zip,last,first[,docket_type]")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
