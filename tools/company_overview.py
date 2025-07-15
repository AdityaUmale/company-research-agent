# tools/company_overview.py (Fixed Version with Better Error Handling)
import re
import json
import requests
from urllib.parse import urlparse, urljoin
from tools.website_scraper import session
from tools.wikipedia_lookup import get_company_wikipedia_summary
from tools.website_scraper import scrape_company_about
import time

def clean_description(raw_text):
    """Clean and deduplicate description text"""
    if not raw_text:
        return None
    
    # Split into sentences and deduplicate
    sentences = raw_text.split('\n')
    unique_sentences = []
    seen = set()
    
    for sentence in sentences:
        cleaned = sentence.strip()
        if cleaned and cleaned not in seen and len(cleaned) > 10:
            unique_sentences.append(cleaned)
            seen.add(cleaned)
    
    # Take first 3 unique sentences and join them
    return ' '.join(unique_sentences[:3])

def extract_employee_count_from_text(text):
    """Extract employee count from text using regex patterns"""
    if not text:
        return None
    
    # Common patterns for employee count
    patterns = [
        r'(\d{1,3}(?:,\d{3})*)\s*(?:employees?|staff|workforce|team members?|people)',
        r'(?:employs?|has)\s*(\d{1,3}(?:,\d{3})*)\s*(?:employees?|staff|people)',
        r'(?:team|workforce|staff)\s*of\s*(\d{1,3}(?:,\d{3})*)',
        r'(\d{1,3}(?:,\d{3})*)\+?\s*(?:employees?|staff)',
        r'over\s*(\d{1,3}(?:,\d{3})*)\s*(?:employees?|staff)',
        r'more than\s*(\d{1,3}(?:,\d{3})*)\s*(?:employees?|staff)',
        r'approximately\s*(\d{1,3}(?:,\d{3})*)\s*(?:employees?|staff)',
        r'around\s*(\d{1,3}(?:,\d{3})*)\s*(?:employees?|staff)'
    ]
    
    for pattern in patterns:
        try:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                # Return the largest number found (most likely to be accurate)
                numbers = [int(match.replace(',', '')) for match in matches]
                return max(numbers)
        except Exception:
            continue
    
    return None

def extract_office_locations_from_text(text):
    """Extract office locations from text"""
    if not text:
        return []
    
    locations = []
    
    # Patterns for office locations
    patterns = [
        r'(?:offices?|locations?|presence)\s*in\s*([^.]+)',
        r'(?:operates?|located)\s*in\s*([^.]+)',
        r'(?:branches?|facilities?)\s*in\s*([^.]+)',
        r'(?:headquarters?|HQ)\s*in\s*([^.]+)',
        r'(?:based|situated)\s*in\s*([^.]+)',
        r'(?:global|international)\s*(?:offices?|presence)\s*(?:in|across)\s*([^.]+)'
    ]
    
    for pattern in patterns:
        try:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Clean and split locations
                match = re.sub(r'\([^)]*\)', '', match)  # Remove parentheses
                match = match.strip()
                if match and len(match) > 2:
                    # Split by common delimiters
                    sublocs = re.split(r'[,;&]| and ', match)
                    for loc in sublocs:
                        loc = loc.strip()
                        if loc and len(loc) > 2:
                            locations.append(loc)
        except Exception:
            continue
    
    # Remove duplicates and clean
    unique_locations = []
    seen = set()
    for loc in locations:
        loc_clean = loc.lower().strip()
        if loc_clean not in seen and len(loc_clean) > 2:
            unique_locations.append(loc)
            seen.add(loc_clean)
    
    return unique_locations[:10]  # Limit to 10 locations

def scrape_careers_page(base_url):
    """Scrape careers/jobs page for employee count and office locations with timeout"""
    print(f"🔍 Checking careers page...")
    
    careers_paths = [
        '/careers', '/jobs', '/about/careers', '/company/careers',
        '/work-with-us', '/join-us', '/employment', '/career'
    ]
    
    for path in careers_paths:
        try:
            url = urljoin(base_url, path)
            print(f"  Trying: {url}")
            
            # Add shorter timeout and headers
            response = session.get(url, timeout=5, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            if response.status_code == 200:
                print(f"  ✅ Found careers page")
                text = response.text
                
                # Extract employee count
                employee_count = extract_employee_count_from_text(text)
                
                # Extract office locations
                locations = extract_office_locations_from_text(text)
                
                if employee_count or locations:
                    return {
                        'employee_count': employee_count,
                        'office_locations': locations,
                        'source_url': url
                    }
        except Exception as e:
            print(f"  ❌ Error with {path}: {str(e)[:50]}...")
            continue
    
    print(f"  ❌ No careers page found")
    return None

def scrape_about_page_for_headcount(base_url):
    """Scrape about page specifically for employee count and locations with timeout"""
    print(f"🔍 Checking about page for headcount...")
    
    about_paths = [
        '/about', '/about-us', '/company', '/who-we-are',
        '/our-company', '/company/about', '/about/company'
    ]
    
    for path in about_paths:
        try:
            url = urljoin(base_url, path)
            print(f"  Trying: {url}")
            
            response = session.get(url, timeout=5, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            if response.status_code == 200:
                print(f"  ✅ Found about page")
                text = response.text
                
                # Extract employee count
                employee_count = extract_employee_count_from_text(text)
                
                # Extract office locations
                locations = extract_office_locations_from_text(text)
                
                if employee_count or locations:
                    return {
                        'employee_count': employee_count,
                        'office_locations': locations,
                        'source_url': url
                    }
        except Exception as e:
            print(f"  ❌ Error with {path}: {str(e)[:50]}...")
            continue
    
    print(f"  ❌ No useful about page found")
    return None

def get_linkedin_company_data(company_name):
    """Try to get company data from LinkedIn with timeout"""
    print(f"🔍 Checking LinkedIn...")
    
    try:
        # Create a search query for LinkedIn company page
        query = company_name.replace(' ', '-').lower()
        linkedin_url = f"https://www.linkedin.com/company/{query}"
        
        print(f"  Trying: {linkedin_url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(linkedin_url, headers=headers, timeout=5)
        if response.status_code == 200:
            print(f"  ✅ Found LinkedIn page")
            text = response.text
            
            # Extract employee count from LinkedIn
            employee_patterns = [
                r'(\d{1,3}(?:,\d{3})*)\s*employees?',
                r'(\d{1,3}(?:,\d{3})*)\s*people'
            ]
            
            for pattern in employee_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    return {
                        'employee_count': int(matches[0].replace(',', '')),
                        'source_url': linkedin_url
                    }
        else:
            print(f"  ❌ LinkedIn returned {response.status_code}")
    except Exception as e:
        print(f"  ❌ LinkedIn error: {str(e)[:50]}...")
    
    return None

def extract_founding_date(wiki_data):
    """Extract founding date from Wikipedia data"""
    if not wiki_data or not wiki_data.get('summary'):
        return None
    
    text = wiki_data['summary']
    
    # Common patterns for founding dates
    patterns = [
        r'founded in (\d{4})',
        r'established in (\d{4})',
        r'incorporated in (\d{4})',
        r'founded on.*?(\d{4})',
        r'established on.*?(\d{4})',
        r'founded.*?(\d{4})',
        r'established.*?(\d{4})',
        r'formed in (\d{4})',
        r'created in (\d{4})'
    ]
    
    for pattern in patterns:
        try:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        except Exception:
            continue
    
    return None

def extract_founders(wiki_data):
    """Extract founders from Wikipedia data"""
    if not wiki_data or not wiki_data.get('summary'):
        return None
    
    text = wiki_data['summary']
    
    # Common patterns for founders
    patterns = [
        r'founded by ([^.]+)',
        r'co-founded by ([^.]+)',
        r'founder[s]? ([^.]+)',
        r'established by ([^.]+)',
        r'created by ([^.]+)'
    ]
    
    for pattern in patterns:
        try:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                founders_text = match.group(1)
                # Clean and split founders
                founders_text = re.sub(r'\([^)]*\)', '', founders_text)  # Remove parentheses
                founders = [f.strip() for f in re.split(r'[,&]| and ', founders_text)]
                return [f for f in founders if f and len(f) > 2]
        except Exception:
            continue
    
    return None

def extract_headquarters(wiki_data):
    """Extract headquarters location from Wikipedia data"""
    if not wiki_data or not wiki_data.get('summary'):
        return None
    
    text = wiki_data['summary']
    
    # Common patterns for headquarters
    patterns = [
        r'headquartered in ([^.]+)',
        r'headquarters in ([^.]+)',
        r'based in ([^.]+)',
        r'located in ([^.]+)',
        r'headquarters[:]? ([^.]+)',
        r'HQ[:]? ([^.]+)'
    ]
    
    for pattern in patterns:
        try:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                location = match.group(1).strip()
                # Clean location text
                location = re.sub(r'\([^)]*\)', '', location)  # Remove parentheses
                location = location.replace(',', ', ').strip()
                return location
        except Exception:
            continue
    
    return None

def extract_ownership(wiki_data):
    """Extract ownership structure from Wikipedia data"""
    if not wiki_data or not wiki_data.get('summary'):
        return None
    
    text = wiki_data['summary']
    
    # Common patterns for ownership
    public_patterns = [
        r'publicly traded',
        r'public company',
        r'listed on',
        r'trades on',
        r'NASDAQ',
        r'NYSE',
        r'stock exchange'
    ]
    
    private_patterns = [
        r'private company',
        r'privately held',
        r'private corporation'
    ]
    
    subsidiary_patterns = [
        r'subsidiary of ([^.]+)',
        r'owned by ([^.]+)',
        r'division of ([^.]+)'
    ]
    
    try:
        # Check for subsidiary first
        for pattern in subsidiary_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                parent = match.group(1).strip()
                return f"Subsidiary of {parent}"
        
        # Check for public company
        for pattern in public_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return "Publicly traded"
        
        # Check for private company
        for pattern in private_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return "Private company"
    except Exception:
        pass
    
    return None

def extract_company_basics(wiki_data):
    """Extract basic company info from Wikipedia data"""
    if not wiki_data:
        return {}
    
    return {
        'founded': extract_founding_date(wiki_data),
        'founders': extract_founders(wiki_data),
        'headquarters': extract_headquarters(wiki_data),
        'ownership': extract_ownership(wiki_data)
    }

def extract_company_history(wiki_data):
    """Extract company history from Wikipedia data"""
    if not wiki_data or not wiki_data.get('summary'):
        return None
    
    text = wiki_data['summary']
    
    # Look for history-related sentences
    sentences = text.split('.')
    history_sentences = []
    
    history_keywords = [
        'history', 'founded', 'established', 'started', 'began',
        'originally', 'initially', 'first', 'early', 'development'
    ]
    
    try:
        for sentence in sentences:
            sentence = sentence.strip()
            if any(keyword in sentence.lower() for keyword in history_keywords):
                if len(sentence) > 20:  # Meaningful sentences
                    history_sentences.append(sentence)
        
        if history_sentences:
            return '. '.join(history_sentences[:3]) + '.'
    except Exception:
        pass
    
    return None

def research_company_overview(company_name: str) -> dict:
    """
    Enhanced version that includes employee count and office locations.
    Returns a structured dict suitable for the final report.
    """
    print(f"🔍 Starting company overview research for: {company_name}")
    
    overview = {
        "name": company_name,
        "description": None,
        "founded": None,
        "founders": None,
        "ownership": None,
        "headquarters": None,
        "history": None,
        "employee_count": None,
        "office_locations": [],
        "sources": [],
        "confidence_score": 0.0
    }
    
    # 1. Fetch Wikipedia data first
    print("📖 Fetching Wikipedia data...")
    wiki_data = get_company_wikipedia_summary(company_name)
    
    # 2. Derive base URL for scraping
    base_url = None
    if wiki_data and wiki_data.get("url"):
        parsed = urlparse(wiki_data["url"])
        if "wikipedia.org" not in parsed.netloc:
            base_url = f"{parsed.scheme}://{parsed.netloc}"
    
    # 3. Fallback: derive domain from company name
    if not base_url:
        print("🔗 Deriving company URL...")
        tokens = re.sub(r"[^a-z0-9 ]", "", company_name.lower()).split()
        if tokens:
            main_token = tokens[0]
        else:
            main_token = re.sub(r"[^a-z0-9]", "", company_name.lower())
        
        possible_domains = [f"https://www.{main_token}.com", f"https://{main_token}.com"]
        
        for url in possible_domains:
            try:
                print(f"  Testing: {url}")
                resp = session.head(url, timeout=3)
                if resp.status_code == 200:
                    base_url = url
                    print(f"  ✅ Found: {url}")
                    break
            except Exception as e:
                print(f"  ❌ Failed: {str(e)[:30]}...")
                continue
        
        if not base_url:
            base_url = possible_domains[0]
            print(f"  🔄 Using fallback: {base_url}")
    
    # 4. Scrape the official About page
    print("🌐 Scraping official website...")
    try:
        site_data = scrape_company_about(base_url)
        if site_data:
            overview["sources"].append({
                "type": "Official Website",
                "title": "About Page",
                "url": site_data.get("about_page_url")
            })
            
            raw_description = site_data.get("content_excerpt")
            overview["description"] = clean_description(raw_description)
            overview["confidence_score"] += site_data.get("confidence_score", 0)
            print("  ✅ Official website scraped")
    except Exception as e:
        print(f"  ❌ Official website error: {str(e)[:50]}...")
    
    # 5. NEW: Scrape careers page (with timeout protection)
    try:
        careers_data = scrape_careers_page(base_url)
        if careers_data:
            overview["sources"].append({
                "type": "Official Website",
                "title": "Careers Page",
                "url": careers_data.get("source_url")
            })
            
            if careers_data.get("employee_count"):
                overview["employee_count"] = careers_data["employee_count"]
                print(f"  ✅ Found employee count: {careers_data['employee_count']}")
            
            if careers_data.get("office_locations"):
                overview["office_locations"].extend(careers_data["office_locations"])
                print(f"  ✅ Found {len(careers_data['office_locations'])} office locations")
            
            overview["confidence_score"] += 0.1
    except Exception as e:
        print(f"❌ Careers page error: {str(e)[:50]}...")
    
    # 6. NEW: Scrape about page for additional headcount info
    try:
        about_headcount = scrape_about_page_for_headcount(base_url)
        if about_headcount:
            if about_headcount.get("employee_count") and not overview["employee_count"]:
                overview["employee_count"] = about_headcount["employee_count"]
                print(f"  ✅ Found employee count from about: {about_headcount['employee_count']}")
            
            if about_headcount.get("office_locations"):
                overview["office_locations"].extend(about_headcount["office_locations"])
                print(f"  ✅ Found additional office locations")
            
            overview["confidence_score"] += 0.05
    except Exception as e:
        print(f"❌ About page headcount error: {str(e)[:50]}...")
    
    # 7. NEW: Try LinkedIn (with timeout protection)
    try:
        linkedin_data = get_linkedin_company_data(company_name)
        if linkedin_data:
            overview["sources"].append({
                "type": "LinkedIn",
                "title": "Company Page",
                "url": linkedin_data.get("source_url")
            })
            
            if linkedin_data.get("employee_count") and not overview["employee_count"]:
                overview["employee_count"] = linkedin_data["employee_count"]
                print(f"  ✅ Found employee count from LinkedIn: {linkedin_data['employee_count']}")
            
            overview["confidence_score"] += 0.15
    except Exception as e:
        print(f"❌ LinkedIn error: {str(e)[:50]}...")
    
    # 8. Extract data from Wikipedia
    if wiki_data:
        print("📖 Processing Wikipedia data...")
        overview["sources"].append({
            "type": "Wikipedia",
            "title": wiki_data.get("title"),
            "url": wiki_data.get("url")
        })
        
        try:
            basics = extract_company_basics(wiki_data)
            overview["founded"] = basics.get("founded")
            overview["founders"] = basics.get("founders")
            overview["headquarters"] = basics.get("headquarters")
            overview["ownership"] = basics.get("ownership")
            overview["history"] = extract_company_history(wiki_data)
            
            # Extract employee count and locations from Wikipedia
            wiki_text = wiki_data.get("summary", "")
            if not overview["employee_count"]:
                overview["employee_count"] = extract_employee_count_from_text(wiki_text)
            
            wiki_locations = extract_office_locations_from_text(wiki_text)
            overview["office_locations"].extend(wiki_locations)
            
            if not overview.get("description"):
                raw_wiki_summary = wiki_data.get("summary")
                overview["description"] = clean_description(raw_wiki_summary)
            
            overview["confidence_score"] += wiki_data.get("confidence_score", 0)
            print("  ✅ Wikipedia data processed")
        except Exception as e:
            print(f"  ❌ Wikipedia processing error: {str(e)[:50]}...")
    
    # 9. Clean up office locations (remove duplicates)
    unique_locations = []
    seen = set()
    for loc in overview["office_locations"]:
        loc_clean = loc.lower().strip()
        if loc_clean not in seen:
            unique_locations.append(loc)
            seen.add(loc_clean)
    
    overview["office_locations"] = unique_locations[:15]  # Limit to 15 locations
    
    # 10. Normalize confidence score
    max_score = 1.9  # Adjusted for new features
    overview["confidence_score"] = round(min(overview["confidence_score"] / max_score, 1.0), 2)
    
    # 11. Additional confidence adjustments
    completeness_score = 0
    fields_to_check = ['description', 'founded', 'founders', 'headquarters', 'ownership', 'employee_count']
    
    for field in fields_to_check:
        if overview.get(field):
            completeness_score += 0.1
    
    # Boost for office locations
    if overview.get("office_locations"):
        completeness_score += 0.05
    
    if completeness_score >= 0.4:
        overview["confidence_score"] = min(overview["confidence_score"] + 0.1, 1.0)
    
    overview["confidence_score"] = round(overview["confidence_score"], 2)
    
    print(f"✅ Research completed with confidence: {overview['confidence_score']}")
    return overview

def display_company_overview(overview):
    """Display enhanced company overview"""
    print(f"\n{'='*60}")
    print(f"🏢 COMPANY OVERVIEW: {overview['name'].upper()}")
    print(f"{'='*60}")
    
    if overview.get('description'):
        print(f"📝 Description: {overview['description']}")
    
    if overview.get('founded'):
        print(f"📅 Founded: {overview['founded']}")
    
    if overview.get('founders'):
        founders = overview['founders']
        if isinstance(founders, list):
            print(f"👥 Founders: {', '.join(founders)}")
        else:
            print(f"👥 Founders: {founders}")
    
    if overview.get('headquarters'):
        print(f"🏛️ Headquarters: {overview['headquarters']}")
    
    if overview.get('ownership'):
        print(f"🏢 Ownership: {overview['ownership']}")
    
    # NEW: Display employee count
    if overview.get('employee_count'):
        print(f"👥 Employee Count: {overview['employee_count']:,}")
    
    # NEW: Display office locations
    if overview.get('office_locations'):
        print(f"🌍 Office Locations: {', '.join(overview['office_locations'])}")
    
    if overview.get('history'):
        print(f"📚 History: {overview['history']}")
    
    print(f"\n🎯 Confidence Score: {overview['confidence_score']}/1.00")
    
    print(f"\n📖 Sources:")
    for i, source in enumerate(overview['sources'], 1):
        print(f"   {i}. {source['type']}: {source['title']} - {source['url']}")
    
    print(f"\n{'='*60}")

# Test function
if __name__ == "__main__":
    result = research_company_overview("Tesla, Inc.")
    display_company_overview(result)