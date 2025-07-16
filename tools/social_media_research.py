
import requests
from bs4 import BeautifulSoup
import time
import json
import re
from urllib.parse import urljoin, urlparse
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

class SocialMediaResearcher:
    def __init__(self, company_name, delay=3, use_selenium=False):
        self.company_name = company_name
        self.delay = delay
        self.use_selenium = use_selenium
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.results = {
            'linkedin': {},
            'twitter': {},
            'instagram': {},
            'facebook': {},
            'youtube': {},
            'confidence_score': 0.0,
            'sources': []
        }
        
        if use_selenium:
            self.setup_selenium()
    
    def setup_selenium(self):
        """Setup headless Chrome driver"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            print("✅ Selenium WebDriver initialized")
        except Exception as e:
            print(f"❌ Selenium setup failed: {e}")
            self.use_selenium = False
            self.driver = None
    
    def research_all_platforms(self):
        """Main orchestrator method"""
        try:
            print(f"🔍 Starting social media research for: {self.company_name}")
            print(f"🔧 Using Selenium: {'Yes' if self.use_selenium else 'No'}")
            
            # LinkedIn Company Page
            print("\n🔗 Researching LinkedIn...")
            self.research_linkedin()
            time.sleep(self.delay)
            
            # Twitter/X Profile
            print("\n🐦 Researching Twitter/X...")
            self.research_twitter()
            time.sleep(self.delay)
            
            # Instagram Business Profile
            print("\n📸 Researching Instagram...")
            self.research_instagram()
            time.sleep(self.delay)
            
            # Facebook Page
            print("\n📘 Researching Facebook...")
            self.research_facebook()
            time.sleep(self.delay)
            
            # YouTube Channel
            print("\n🎥 Researching YouTube...")
            self.research_youtube()
            
            # Calculate overall confidence
            self.calculate_confidence()
            
            if self.use_selenium and self.driver:
                self.driver.quit()
            
            return self.results
            
        except Exception as e:
            logging.error(f"Error in social media research: {e}")
            if self.use_selenium and self.driver:
                self.driver.quit()
            return self.results
    
    def get_with_selenium(self, url, wait_for_element=None, timeout=10):
        """Get page content with Selenium"""
        if not self.use_selenium or not self.driver:
            return None
            
        try:
            self.driver.get(url)
            
            if wait_for_element:
                WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, wait_for_element))
                )
            else:
                time.sleep(3)  # General wait for page load
                
            return self.driver.page_source
            
        except TimeoutException:
            print(f"  ⏱️ Timeout waiting for element: {wait_for_element}")
            return self.driver.page_source
        except Exception as e:
            print(f"  ❌ Selenium error: {str(e)[:50]}...")
            return None
    
    def research_linkedin(self):
        """Research LinkedIn company page"""
        try:
            if self.company_name.lower() == "meta":
                linkedin_urls = [
                    "https://www.linkedin.com/company/meta",
                    "https://www.linkedin.com/company/meta-platforms",
                ]
            else:
                linkedin_urls = [
                    f"https://www.linkedin.com/company/{self.company_name.lower().replace(' ', '-').replace(',', '').replace('.', '')}",
                    f"https://www.linkedin.com/company/{self.company_name.lower().replace(' ', '').replace(',', '').replace('.', '')}",
                ]
            
            for url in linkedin_urls:
                try:
                    print(f"  Trying: {url}")
                    
                    # Try with Selenium first if available
                    if self.use_selenium:
                        html = self.get_with_selenium(url, '[data-test-id="about-us-description"]')
                        if html:
                            soup = BeautifulSoup(html, 'html.parser')
                            linkedin_data = self.parse_linkedin_page(soup, url)
                            if linkedin_data and linkedin_data['found']:
                                self.results['linkedin'] = linkedin_data
                                self.results['sources'].append({
                                    'platform': 'LinkedIn',
                                    'url': url,
                                    'method': 'selenium',
                                    'status': 'success'
                                })
                                print(f"  ✅ Found LinkedIn page (Selenium)")
                                return
                    
                    # Fallback to requests
                    response = self.session.get(url, timeout=15)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        linkedin_data = self.parse_linkedin_page(soup, url)
                        if linkedin_data and linkedin_data['found']:
                            self.results['linkedin'] = linkedin_data
                            self.results['sources'].append({
                                'platform': 'LinkedIn',
                                'url': url,
                                'method': 'requests',
                                'status': 'success'
                            })
                            print(f"  ✅ Found LinkedIn page (Requests)")
                            return
                    else:
                        print(f"  ❌ HTTP {response.status_code}")
                            
                except Exception as e:
                    print(f"  ❌ Error: {str(e)[:50]}...")
                    continue
                    
        except Exception as e:
            logging.error(f"LinkedIn research error: {e}")
    
    def parse_linkedin_page(self, soup, url):
        """Parse LinkedIn company page data with better selectors"""
        data = {
            'url': url,
            'followers': None,
            'employees': None,
            'description': None,
            'industry': None,
            'found': False
        }
        
        try:
            # Multiple strategies for follower count
            follower_selectors = [
                '.org-top-card-summary-info-list__info-item',
                '.org-about-company-module__company-staff-count-range',
                '[data-test-id="about-us-description"]'
            ]
            
            # Look for followers in text content
            text_content = soup.get_text()
            
            # Pattern for follower count
            follower_patterns = [
                r'([\d,]+)\s*followers',
                r'([\d,]+)\s*follower',
                r'followers[:\s]+([\d,]+)',
            ]
            
            for pattern in follower_patterns:
                match = re.search(pattern, text_content, re.IGNORECASE)
                if match:
                    followers = match.group(1).replace(',', '')
                    if followers.isdigit() and int(followers) > 1000:  # Sanity check
                        data['followers'] = f"{int(followers):,} followers"
                        data['found'] = True
                        break
            
            # Look for employee count
            employee_patterns = [
                r'([\d,]+)\s*employees',
                r'employees[:\s]+([\d,]+)',
            ]
            
            for pattern in employee_patterns:
                match = re.search(pattern, text_content, re.IGNORECASE)
                if match:
                    employees = match.group(1).replace(',', '')
                    if employees.isdigit() and int(employees) > 10:  # Sanity check
                        data['employees'] = f"{int(employees):,} employees"
                        data['found'] = True
                        break
            
            # Look for description
            desc_selectors = [
                '[data-test-id="about-us-description"]',
                '.org-about-us-organization-description__text',
                '.org-about-company-module__company-description'
            ]
            
            for selector in desc_selectors:
                desc_elem = soup.select_one(selector)
                if desc_elem:
                    desc_text = desc_elem.get_text().strip()
                    if len(desc_text) > 50:  # Ensure it's substantial
                        data['description'] = desc_text[:300] + "..." if len(desc_text) > 300 else desc_text
                        data['found'] = True
                        break
                
        except Exception as e:
            logging.error(f"Error parsing LinkedIn page: {e}")
        
        return data
    
    def research_twitter(self):
        """Research Twitter/X profile with better parsing"""
        try:
            if self.company_name.lower() == "meta":
                twitter_handles = ["meta", "meta-platforms"]
            else:
                twitter_handles = [
                    self.company_name.lower().replace(' ', '').replace(',', '').replace('.', ''),
                    self.company_name.split()[0].lower(),
                ]
            
            for handle in twitter_handles:
                url = f"https://twitter.com/{handle}"
                try:
                    print(f"  Trying: {url}")
                    
                    # Try with Selenium first
                    if self.use_selenium:
                        html = self.get_with_selenium(url, '[data-testid="UserName"]')
                        if html:
                            twitter_data = self.parse_twitter_page(html, url, handle)
                            if twitter_data and twitter_data['found']:
                                self.results['twitter'] = twitter_data
                                self.results['sources'].append({
                                    'platform': 'Twitter',
                                    'url': url,
                                    'method': 'selenium',
                                    'status': 'success'
                                })
                                print(f"  ✅ Found Twitter profile (Selenium)")
                                return
                    
                    # Fallback to requests
                    response = self.session.get(url, timeout=15)
                    if response.status_code == 200:
                        twitter_data = self.parse_twitter_page(response.text, url, handle)
                        if twitter_data and twitter_data['found']:
                            self.results['twitter'] = twitter_data
                            self.results['sources'].append({
                                'platform': 'Twitter',
                                'url': url,
                                'method': 'requests',
                                'status': 'success'
                            })
                            print(f"  ✅ Found Twitter profile (Requests)")
                            return
                    else:
                        print(f"  ❌ HTTP {response.status_code}")
                            
                except Exception as e:
                    print(f"  ❌ Error: {str(e)[:50]}...")
                    continue
                    
        except Exception as e:
            logging.error(f"Twitter research error: {e}")
    
    def parse_twitter_page(self, html, url, handle):
        """Parse Twitter profile with better patterns"""
        data = {
            'url': url,
            'handle': handle,
            'followers': None,
            'following': None,
            'found': False
        }
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            stat_links = soup.find_all('a', class_='r-rjixqe')
            if len(stat_links) >= 2:
                following_text = stat_links[0].text.strip()
                followers_text = stat_links[1].text.strip()
                # Extract numbers, assuming format like '123 Following' and '456 Followers'
                data['following'] = following_text.split()[0]
                data['followers'] = followers_text.split()[0]
                data['found'] = True
        except Exception as e:
            logging.error(f"Error parsing Twitter page: {e}")
        
        return data
    
    def research_instagram(self):
        """Research Instagram with better parsing"""
        try:
            if self.company_name.lower() == "meta":
                instagram_handles = ["meta", "meta-platforms"]
            else:
                instagram_handles = [
                    self.company_name.lower().replace(' ', '').replace(',', '').replace('.', ''),
                    self.company_name.split()[0].lower(),
                ]
            
            for handle in instagram_handles:
                url = f"https://www.instagram.com/{handle}/"
                try:
                    print(f"  Trying: {url}")
                    
                    # Try with Selenium first
                    if self.use_selenium:
                        html = self.get_with_selenium(url, 'meta[property="og:description"]')
                        if html:
                            instagram_data = self.parse_instagram_page(html, url, handle)
                            if instagram_data and instagram_data['found']:
                                self.results['instagram'] = instagram_data
                                self.results['sources'].append({
                                    'platform': 'Instagram',
                                    'url': url,
                                    'method': 'selenium',
                                    'status': 'success'
                                })
                                print(f"  ✅ Found Instagram profile (Selenium)")
                                return
                    
                    # Fallback to requests
                    response = self.session.get(url, timeout=15)
                    if response.status_code == 200:
                        instagram_data = self.parse_instagram_page(response.text, url, handle)
                        if instagram_data and instagram_data['found']:
                            self.results['instagram'] = instagram_data
                            self.results['sources'].append({
                                'platform': 'Instagram',
                                'url': url,
                                'method': 'requests',
                                'status': 'success'
                            })
                            print(f"  ✅ Found Instagram profile (Requests)")
                            return
                    else:
                        print(f"  ❌ HTTP {response.status_code}")
                            
                except Exception as e:
                    print(f"  ❌ Error: {str(e)[:50]}...")
                    continue
                    
        except Exception as e:
            logging.error(f"Instagram research error: {e}")
    
    def parse_instagram_page(self, html, url, handle):
        """Parse Instagram with multiple strategies"""
        data = {
            'url': url,
            'handle': handle,
            'followers': None,
            'posts': None,
            'found': False
        }
        
        try:
            # Multiple patterns for follower count
            follower_patterns = [
                r'"edge_followed_by":{"count":(\d+)}',
                r'"followers":(\d+)',
                r'content="(\d+(?:\.\d+)?[KM]?)\s*Followers',
                r'(\d+(?:\.\d+)?[KM]?)\s*followers',
                r'property="og:description".*?(\d+(?:\.\d+)?[KM]?)\s*Followers'
            ]
            
            for pattern in follower_patterns:
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    followers = match.group(1)
                    # Convert raw numbers to readable format
                    if followers.isdigit() and len(followers) > 6:
                        followers_int = int(followers)
                        if followers_int >= 1000000:
                            followers = f"{followers_int / 1000000:.1f}M"
                        elif followers_int >= 1000:
                            followers = f"{followers_int / 1000:.1f}K"
                    data['followers'] = followers
                    data['found'] = True
                    break
                    
        except Exception as e:
            logging.error(f"Error parsing Instagram page: {e}")
        
        return data
    
    def research_youtube(self):
        """Research YouTube with better parsing"""
        try:
            if self.company_name.lower() == "meta":
                youtube_channels = [
                    "https://www.youtube.com/@meta",
                    "https://www.youtube.com/c/meta-platforms",
                    "https://www.youtube.com/user/meta-platforms"
                ]
            else:
                youtube_channels = [
                    f"https://www.youtube.com/@{self.company_name.lower().replace(' ', '').replace(',', '').replace('.', '')}",
                    f"https://www.youtube.com/c/{self.company_name.replace(' ', '').replace(',', '').replace('.', '')}"
                ]
            
            for url in youtube_channels:
                try:
                    print(f"  Trying: {url}")
                    
                    # Try with Selenium first
                    if self.use_selenium:
                        html = self.get_with_selenium(url, 'yt-formatted-string#subscriber-count')
                        if html:
                            youtube_data = self.parse_youtube_page(html, url)
                            if youtube_data and youtube_data['found']:
                                self.results['youtube'] = youtube_data
                                self.results['sources'].append({
                                    'platform': 'YouTube',
                                    'url': url,
                                    'method': 'selenium',
                                    'status': 'success'
                                })
                                print(f"  ✅ Found YouTube channel (Selenium)")
                                return
                    
                    # Fallback to requests
                    response = self.session.get(url, timeout=15)
                    if response.status_code == 200:
                        youtube_data = self.parse_youtube_page(response.text, url)
                        if youtube_data and youtube_data['found']:
                            self.results['youtube'] = youtube_data
                            self.results['sources'].append({
                                'platform': 'YouTube',
                                'url': url,
                                'method': 'requests',
                                'status': 'success'
                            })
                            print(f"  ✅ Found YouTube channel (Requests)")
                            return
                    else:
                        print(f"  ❌ HTTP {response.status_code}")
                            
                except Exception as e:
                    print(f"  ❌ Error: {str(e)[:50]}...")
                    continue
                    
        except Exception as e:
            logging.error(f"YouTube research error: {e}")
    
    def parse_youtube_page(self, html, url):
        """Parse YouTube with better patterns"""
        data = {
            'url': url,
            'subscribers': None,
            'videos': None,
            'found': False
        }
        
        try:
            # Multiple patterns for subscriber count
            sub_patterns = [
                r'"subscriberCountText":{"simpleText":"([\d.KM]+)\s*subscribers"',
                r'"subscriberCountText":{"runs":\[{"text":"([\d.KM]+)"}.*?"subscribers"',
                r'(\d+(?:\.\d+)?[KM]?)\s*subscribers',
                r'subscribers.*?(\d+(?:\.\d+)?[KM]?)',
                r'"subscriberCount":"(\d+)"'
            ]
            
            for pattern in sub_patterns:
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    subscribers = match.group(1)
                    # Convert raw numbers to readable format
                    if subscribers.isdigit() and len(subscribers) > 6:
                        subs_int = int(subscribers)
                        if subs_int >= 1000000:
                            subscribers = f"{subs_int / 1000000:.1f}M"
                        elif subs_int >= 1000:
                            subscribers = f"{subs_int / 1000:.1f}K"
                    data['subscribers'] = subscribers
                    data['found'] = True
                    break
                    
        except Exception as e:
            logging.error(f"Error parsing YouTube page: {e}")
        
        return data
    
    def research_facebook(self):
        """Research Facebook - often blocked, so we'll skip for now"""
        print("  ⚠️  Facebook research skipped (frequently blocked)")
        pass
    
    def calculate_confidence(self):
        """Calculate confidence score based on found platforms"""
        platforms_found = 0
        total_platforms = 4  # Excluding Facebook for now
        
        for platform in ['linkedin', 'twitter', 'instagram', 'youtube']:
            if self.results[platform] and self.results[platform].get('found', False):
                platforms_found += 1
        
        self.results['confidence_score'] = platforms_found / total_platforms
    
    def generate_report(self):
        """Generate formatted report"""
        print("\n" + "=" * 80)
        print(f"🌐 SOCIAL MEDIA RESEARCH: {self.company_name}")
        print("=" * 80)
        
        for platform, data in self.results.items():
            if data and platform not in ['confidence_score', 'sources'] and data.get('found', False):
                print(f"\n📱 {platform.upper()}:")
                for key, value in data.items():
                    if value and key not in ['found']:
                        print(f"   • {key}: {value}")
        
        print(f"\n🎯 Confidence Score: {self.results['confidence_score']:.2f}")
        platforms_found = len([p for p in self.results if self.results[p] and p not in ['confidence_score', 'sources'] and self.results[p].get('found', False)])
        print(f"📊 Platforms Found: {platforms_found}/4")
        
        if self.results['sources']:
            print(f"\n📖 Sources:")
            for i, source in enumerate(self.results['sources'], 1):
                method = source.get('method', 'unknown')
                print(f"   {i}. {source['platform']} ({method}): {source['url']}")
        
        return {
            'company': self.company_name,
            'research_date': time.strftime('%Y-%m-%d %H:%M:%S'),
            'social_media_presence': self.results,
            'platforms_found': platforms_found
        }

# Test function
def test_social_media_research():
    print("=" * 80)
    print("🧪 TESTING SOCIAL MEDIA RESEARCH")
    print("=" * 80)
    
    # Test with requests only
    print("\n1️⃣ Testing with Requests only:")
    researcher1 = SocialMediaResearcher("Meta", use_selenium=False)
    results1 = researcher1.research_all_platforms()
    report1 = researcher1.generate_report()
    
    print("\n" + "="*50)
    
    # Test with Selenium (if available)
    print("\n2️⃣ Testing with Selenium:")
    researcher2 = SocialMediaResearcher("Meta", use_selenium=True)
    results2 = researcher2.research_all_platforms()
    report2 = researcher2.generate_report()
    
    return report1, report2

if __name__ == "__main__":
    test_social_media_research()