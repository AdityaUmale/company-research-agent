import requests
from bs4 import BeautifulSoup, Tag
from urllib.parse import urljoin
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Optional

# Configure a session with retries
session = requests.Session()
retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("https://", adapter)
session.mount("http://", adapter)



def find_about_url(base_url: str) -> Optional[str]:
    """
    Fetch homepage and look for a link containing 'about' or 'our story'.
    Returns absolute URL if found, else None.
    """
    try:
        res = session.get(base_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if res.status_code != 200:
            return None
        soup = BeautifulSoup(res.text, "html.parser")
        for element in soup.find_all('a', href=True):
            if isinstance(element, Tag):
                text = element.get_text(strip=True).lower()
                href_value = element.get('href')
                if href_value and ('about' in text or 'our story' in text):
                    return urljoin(base_url, str(href_value))
    except Exception:
        return None
    return None



def scrape_company_about(base_url: str) -> Optional[dict]:
    """
    Fetch and parse the 'About' page if available, else fallback to common paths.
    Returns a dict with 'about_page_url', 'content_excerpt', and 'confidence_score'.
    """
    # Attempt dynamic ABOUT page detection
    about_url = find_about_url(base_url)
    if about_url:
        paths_to_try = [about_url]
    else:
        paths = ["/about", "/about-us", "/company", "/our-story", "/"]
        paths_to_try = [urljoin(base_url, path) for path in paths]

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    for full_url in paths_to_try:
        try:
            res = session.get(full_url, headers=headers, timeout=15)
            if res.status_code != 200:
                continue
            soup = BeautifulSoup(res.text, "html.parser")
            paragraphs = soup.find_all("p")
            content_text = [p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 50]
            if not content_text:
                continue
            content = "\n".join(content_text)
            return {
                "about_page_url": full_url,
                "content_excerpt": content[:1000],
                "confidence_score": 0.75
            }
        except Exception as e:
            print(f"[Scraper] Error accessing {full_url}: {e}")
            continue

    print(f"[Scraper] Unable to retrieve 'About' content from {base_url}")
    return None
