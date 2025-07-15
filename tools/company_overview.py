# tools/company_overview.py
import re
from urllib.parse import urlparse
from tools.website_scraper import session
from tools.wikipedia_lookup import get_company_wikipedia_summary
from tools.website_scraper import scrape_company_about

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
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    
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
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            founders_text = match.group(1)
            # Clean and split founders
            founders_text = re.sub(r'\([^)]*\)', '', founders_text)  # Remove parentheses
            founders = [f.strip() for f in re.split(r'[,&]| and ', founders_text)]
            return [f for f in founders if f and len(f) > 2]
    
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
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            location = match.group(1).strip()
            # Clean location text
            location = re.sub(r'\([^)]*\)', '', location)  # Remove parentheses
            location = location.replace(',', ', ').strip()
            return location
    
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
    
    for sentence in sentences:
        sentence = sentence.strip()
        if any(keyword in sentence.lower() for keyword in history_keywords):
            if len(sentence) > 20:  # Meaningful sentences
                history_sentences.append(sentence)
    
    if history_sentences:
        return '. '.join(history_sentences[:3]) + '.'
    
    return None

def research_company_overview(company_name: str) -> dict:
    """
    Combine website scraping and Wikipedia summary to build a company overview.
    Returns a structured dict suitable for the final report.
    """
    overview = {
        "name": company_name,
        "description": None,
        "founded": None,
        "founders": None,
        "ownership": None,
        "headquarters": None,
        "history": None,
        "sources": [],
        "confidence_score": 0.0
    }
    
    # 1. Fetch Wikipedia data first for company summary and structured info
    wiki_data = get_company_wikipedia_summary(company_name)
    
    # 2. Derive base URL for scraping: prefer actual company domain, not Wikipedia
    base_url = None
    if wiki_data and wiki_data.get("url"):
        parsed = urlparse(wiki_data["url"])
        # Avoid using Wikipedia domain for scraping
        if "wikipedia.org" not in parsed.netloc:
            base_url = f"{parsed.scheme}://{parsed.netloc}"
    
    # 3. Fallback: derive domain from company name
    if not base_url:
        # Remove company designators and take first token
        tokens = re.sub(r"[^a-z0-9 ]", "", company_name.lower()).split()
        if tokens:
            main_token = tokens[0]
        else:
            main_token = re.sub(r"[^a-z0-9]", "", company_name.lower())
        
        # Try both 'www' and root domain
        possible_domains = [f"https://www.{main_token}.com", f"https://{main_token}.com"]
        
        for url in possible_domains:
            try:
                # quick HEAD request to check availability
                resp = session.head(url, timeout=5)
                if resp.status_code == 200:
                    base_url = url
                    break
            except Exception:
                continue
        
        if not base_url:
            # fallback to first possible
            base_url = possible_domains[0]
    
    # 4. Scrape the official About page
    site_data = scrape_company_about(base_url)
    if site_data:
        overview["sources"].append({
            "type": "Official Website",
            "title": "About Page",
            "url": site_data.get("about_page_url")
        })
        
        # Clean the description
        raw_description = site_data.get("content_excerpt")
        overview["description"] = clean_description(raw_description)
        overview["confidence_score"] += site_data.get("confidence_score", 0)
    
    # 5. Extract data from Wikipedia
    if wiki_data:
        overview["sources"].append({
            "type": "Wikipedia",
            "title": wiki_data.get("title"),
            "url": wiki_data.get("url")
        })
        
        # Extract basic company info
        basics = extract_company_basics(wiki_data)
        overview["founded"] = basics.get("founded")
        overview["founders"] = basics.get("founders")
        overview["headquarters"] = basics.get("headquarters")
        overview["ownership"] = basics.get("ownership")
        overview["history"] = extract_company_history(wiki_data)
        
        # Only use wiki summary if description is still empty
        if not overview.get("description"):
            raw_wiki_summary = wiki_data.get("summary")
            overview["description"] = clean_description(raw_wiki_summary)
        
        overview["confidence_score"] += wiki_data.get("confidence_score", 0)
    
    # 6. Normalize confidence (max = 0.75 + 0.85)
    max_score = 1.6
    overview["confidence_score"] = round(min(overview["confidence_score"] / max_score, 1.0), 2)
    
    # 7. Additional confidence adjustments based on data completeness
    completeness_score = 0
    fields_to_check = ['description', 'founded', 'founders', 'headquarters', 'ownership']
    
    for field in fields_to_check:
        if overview.get(field):
            completeness_score += 0.1
    
    # Boost confidence if we have most fields filled
    if completeness_score >= 0.3:
        overview["confidence_score"] = min(overview["confidence_score"] + 0.1, 1.0)
    
    overview["confidence_score"] = round(overview["confidence_score"], 2)
    
    return overview

def display_company_overview(overview):
    """Display company overview in a formatted way"""
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