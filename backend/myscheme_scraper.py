import requests
import json
import time

headers = {
    "accept": "application/json, text/plain, */*",
    "origin": "https://www.myscheme.gov.in",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "x-api-key": "tYTy5eEhlu9rFjyxuCr7ra7ACp4dv1RH8gWuHTDc",
    "referer": "https://www.myscheme.gov.in/",
    "accept-language": "en-US,en;q=0.9",
}

base_url = "https://api.myscheme.gov.in/search/v4/schemes"
output_file = "myscheme_api_data.json"

def fetch_all_schemes():
    """Fetch all schemes using the correct API structure"""
    all_schemes = []
    page_size = 20
    offset = 0
    
    print("[🚀] Fetching schemes from MyScheme API...")
    
    while True:
        params = {
            "lang": "en",
            "from": offset,
            "size": page_size,
        }
        
        try:
            print(f"[🔄] Fetching page {offset//page_size + 1} (offset: {offset})...")
            response = requests.get(base_url, headers=headers, params=params, timeout=30)
            
            if response.status_code != 200:
                print(f"[❌] Error fetching data: {response.status_code}")
                print(f"[❌] Response: {response.text[:200]}...")
                break
            
            data = response.json()
            
            schemes = data.get("data", {}).get("hits", {}).get("items", [])
            
            if not schemes:
                print("[✅] No more schemes found. Fetch complete.")
                break
            
            print(f"[📦] Found {len(schemes)} schemes on this page")
            
            for s in schemes:
                if not isinstance(s, dict):
                    print(f"[⚠️] Skipping malformed scheme entry (not a dictionary): {s}")
                    continue 

                fields = s.get("fields", {}) # Get the 'fields' dictionary
                
                # Extract Title and Description
                title = fields.get("schemeName", "N/A")
                description = fields.get("briefDescription", "N/A")

                # Extract Department (prefer nodalMinistryName, fallback to beneficiaryState)
                department = fields.get("nodalMinistryName", "N/A")
                if department is None or department == "N/A":
                    beneficiary_state_list = fields.get("beneficiaryState", [])
                    if isinstance(beneficiary_state_list, list) and beneficiary_state_list:
                        department = ", ".join(beneficiary_state_list)
                    else:
                        department = "N/A" # Default if neither is found or state list is empty

                # Construct Link
                slug = fields.get("slug")
                link = f"https://www.myscheme.gov.in/schemes/{slug}" if slug else "N/A"

                # Extract Category (join list into string if it's a list)
                category_data = fields.get("schemeCategory", "N/A")
                if isinstance(category_data, list):
                    category = ", ".join(category_data)
                else:
                    category = category_data

                # Extract State (join list into string if it's a list)
                state_data = fields.get("beneficiaryState", "N/A")
                if isinstance(state_data, list):
                    state = ", ".join(state_data)
                else:
                    state = state_data

                # Eligibility (age object is complex, keep as raw for now)
                eligibility_age = fields.get("age", "N/A")

                scheme_info = {
                    "title": title,
                    "description": description,
                    "department": department,
                    "link": link,
                    "benefits": "N/A", # Not clearly available in provided snippet
                    "eligibility": eligibility_age, # Represents age-based eligibility, more parsing needed for full detail
                    "category": category,
                    "state": state,
                    "gender": "N/A", # Not clearly available as a direct field
                    "caste": "N/A", # Not clearly available as a direct field (only within age obj)
                    "location": state, # Using state as the primary location info
                }
                all_schemes.append(scheme_info)
            
            offset += page_size
            print(f"[📊] Total schemes collected: {len(all_schemes)}")
            
            total_hits = data.get("data", {}).get("summary", {}).get("total", 0)
            if len(all_schemes) >= total_hits:
                print("[✅] All schemes fetched based on total count.")
                break
            
            time.sleep(1) # Be polite to the API
            
        except Exception as e:
            print(f"[❌] Exception occurred: {e}")
            break
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_schemes, f, indent=4, ensure_ascii=False)
    
    print(f"[💾] Saved {len(all_schemes)} schemes to '{output_file}'")
    
    if all_schemes:
        print(f"\n[📊] Summary:")
        print(f"Total schemes: {len(all_schemes)}")
        
        dept_counts = {}
        for scheme in all_schemes:
            dept = scheme["department"]
            dept_counts[dept] = dept_counts.get(dept, 0) + 1
        
        print("Top 5 departments:")
        for dept, count in sorted(dept_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f" - {dept}: {count}")

def test_single_request():
    """Test and print one API call response for debugging, showing actual scheme items."""
    print("[🧪] Testing single API request...")
    
    params = {
        "lang": "en",
        "from": 0,
        "size": 2, # Get a small number of items to inspect their full structure
    }
    
    try:
        response = requests.get(base_url, headers=headers, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print("[✅] Response received")
            
            schemes_test = data.get("data", {}).get("hits", {}).get("items", [])
            if schemes_test:
                print("\n[📋] Structure of first 2 scheme items:")
                for i, scheme_item in enumerate(schemes_test[:2]):
                    print(f"--- Scheme Item {i+1} ---")
                    print(json.dumps(scheme_item, indent=2))
            else:
                print("[❗] No scheme items found in test request.")

        else:
            print(f"[❌] Status: {response.status_code}, Message: {response.text}")
    except Exception as e:
        print(f"[❌] Exception: {e}")

if __name__ == "__main__":
    test_single_request()
    print("\n" + "="*50)
    fetch_all_schemes() # Re-enabled the full fetch