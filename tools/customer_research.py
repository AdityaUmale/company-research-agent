import requests
import json
import time
from dataclasses import dataclass
from typing import List, Dict, Optional
import re
from urllib.parse import urlencode, quote
import csv
from datetime import datetime
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import urllib.request
import bs4.element

@dataclass
class ClientInfo:
    name: str
    relationship_type: str
    industry: str
    description: str
    source: str

@dataclass
class CustomerSegment:
    segment_name: str
    description: str
    characteristics: List[str]
    size_estimate: str
    source: str

@dataclass
class ResearchResult:
    company_name: str
    major_clients: List[ClientInfo]
    customer_segments: List[CustomerSegment]
    industry_focus: List[str]
    business_model: str
    target_markets: List[str]
    research_timestamp: str

class ClientResearchTool:
    def __init__(self, delay_between_requests=2):
        self.delay = delay_between_requests
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def search_duckduckgo(self, query: str, num_results: int = 10, retries: int = 3) -> List[Dict]:
        """Free search using DuckDuckGo with fallback methods and improved error handling"""
        results = []
        # Method 1: Try DuckDuckGo Instant Answer API with retries
        for attempt in range(retries):
            try:
                instant_url = f"https://api.duckduckgo.com/?q={quote(query)}&format=json&no_html=1"
                response = requests.get(instant_url, headers=self.headers, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('Abstract'):
                        results.append({
                            'title': data.get('Heading', query),
                            'url': data.get('AbstractURL', ''),
                            'snippet': data.get('Abstract', '')
                        })
                    for topic in data.get('RelatedTopics', [])[:3]:
                        if isinstance(topic, dict) and topic.get('Text'):
                            results.append({
                                'title': topic.get('Text', '')[:100],
                                'url': topic.get('FirstURL', ''),
                                'snippet': topic.get('Text', '')
                            })
                    if results:
                        break  # Success, break out of retry loop
            except Exception as e:
                print(f"DuckDuckGo Instant API error (attempt {attempt+1}): {e}")
                time.sleep(2)
        # Method 2: Try HTML scraping if instant API didn't work well
        if len(results) < 3:
            try:
                html_url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
                req = urllib.request.Request(html_url, headers=self.headers)
                response = urllib.request.urlopen(req, timeout=15)
                html = response.read().decode('utf-8')
                soup = BeautifulSoup(html, 'html.parser')
                for result in soup.find_all('div', class_='result')[:num_results]:
                    if not isinstance(result, bs4.element.Tag):
                        continue
                    title_elem = result.find('a', class_='result__a') if isinstance(result, bs4.element.Tag) else None
                    snippet_elem = result.find('a', class_='result__snippet') if isinstance(result, bs4.element.Tag) else None
                    if title_elem and hasattr(title_elem, 'get_text'):
                        title = title_elem.get_text().strip()
                        url_val = title_elem['href'] if isinstance(title_elem, bs4.element.Tag) and 'href' in title_elem.attrs else ''
                        snippet = snippet_elem.get_text().strip() if snippet_elem and hasattr(snippet_elem, 'get_text') else ''
                        results.append({
                            'title': title,
                            'url': url_val,
                            'snippet': snippet
                        })
            except Exception as e:
                print(f"DuckDuckGo HTML scraping error: {e}")
        # Method 3: Fallback to Google (if absolutely necessary)
        if len(results) == 0:
            try:
                google_url = f"https://www.google.com/search?q={quote(query)}"
                response = requests.get(google_url, headers=self.headers, timeout=10)
                if response.status_code == 200:
                    text = response.text
                    if query.lower() in text.lower():
                        results.append({
                            'title': f'Google search results for {query}',
                            'url': google_url,
                            'snippet': f'Found references to {query} in search results'
                        })
            except Exception as e:
                print(f"Google fallback error: {e}")
        if not results:
            print(f"❌ No search results found for '{query}'. Consider checking manually or using a different search engine.")
        return results
    
    def search_wikipedia(self, query: str) -> List[Dict]:
        """Search Wikipedia for company information with multiple approaches"""
        results = []
        
        # Method 1: Try direct page summary
        try:
            search_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(query)}"
            response = requests.get(search_url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('extract'):
                    results.append({
                        'title': data.get('title', '') or '',
                        'url': data.get('content_urls', {}).get('desktop', {}).get('page', '') or '',
                        'snippet': data.get('extract', '') or ''
                    })
            
        except Exception as e:
            print(f"Wikipedia direct search error: {e}")
        
        # Method 2: Try search API if direct didn't work
        if not results:
            try:
                search_url = f"https://en.wikipedia.org/w/api.php?action=query&format=json&list=search&srsearch={quote(query)}&srlimit=3"
                response = requests.get(search_url, headers=self.headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    for page in data.get('query', {}).get('search', []):
                        page_title = page.get('title', '') or ''
                        results.append({
                            'title': page_title,
                            'url': f"https://en.wikipedia.org/wiki/{quote(page_title)}",
                            'snippet': page.get('snippet', '') or ''
                        })
                
            except Exception as e:
                print(f"Wikipedia search API error: {e}")
        
        # Method 3: Try company-specific searches
        if not results and query.lower() not in ['apple', 'amazon', 'google']:  # Avoid ambiguous terms
            try:
                company_query = f"{query} company"
                search_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(company_query)}"
                response = requests.get(search_url, headers=self.headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('extract'):
                        results.append({
                            'title': data.get('title', ''),
                            'url': data.get('content_urls', {}).get('desktop', {}).get('page', ''),
                            'snippet': data.get('extract', '')
                        })
                
            except Exception as e:
                print(f"Wikipedia company search error: {e}")
        
        return results
    
    def add_fallback_data(self, company_name: str) -> tuple:
        """Add fallback data for common companies when APIs fail"""
        fallback_clients = []
        fallback_segments = []
        
        # Known data for major companies (when APIs fail)
        company_data = {
            'apple': {
                'clients': [
                    ClientInfo('Fortune 500 Companies', 'Enterprise Client', 'Various', 'Enterprise device management', 'Known data'),
                    ClientInfo('Educational Institutions', 'Education Client', 'Education', 'iPad and Mac deployments', 'Known data'),
                    ClientInfo('Healthcare Organizations', 'Healthcare Client', 'Healthcare', 'iPad for medical use', 'Known data'),
                    ClientInfo('Creative Professionals', 'B2B Client', 'Creative', 'Mac and Pro software', 'Known data')
                ],
                'segments': [
                    CustomerSegment('Enterprise', 'Large corporations using Apple devices for business', ['Corporate IT', 'BYOD programs'], 'Large', 'Known data'),
                    CustomerSegment('Education', 'Schools and universities', ['K-12 schools', 'Higher education'], 'Large', 'Known data'),
                    CustomerSegment('Healthcare', 'Medical professionals and institutions', ['Hospitals', 'Clinics'], 'Medium', 'Known data'),
                    CustomerSegment('Creative Professionals', 'Designers, video editors, musicians', ['Media production', 'Design agencies'], 'Medium', 'Known data'),
                    CustomerSegment('Developers', 'Software developers and tech companies', ['App development', 'Software companies'], 'Medium', 'Known data')
                ]
            },
            'microsoft': {
                'clients': [
                    ClientInfo('Fortune 500 Companies', 'Enterprise Client', 'Various', 'Office 365 and Azure', 'Known data'),
                    ClientInfo('Government Agencies', 'Government Client', 'Government', 'Windows and Office licensing', 'Known data'),
                    ClientInfo('Educational Institutions', 'Education Client', 'Education', 'Microsoft 365 Education', 'Known data')
                ],
                'segments': [
                    CustomerSegment('Enterprise', 'Large corporations', ['Office productivity', 'Cloud services'], 'Very Large', 'Known data'),
                    CustomerSegment('SMB', 'Small and medium businesses', ['Microsoft 365 Business'], 'Large', 'Known data'),
                    CustomerSegment('Developers', 'Software developers', ['Visual Studio', 'Azure'], 'Medium', 'Known data')
                ]
            },
            'salesforce': {
                'clients': [
                    ClientInfo('T-Mobile', 'Enterprise Client', 'Telecommunications', 'CRM platform', 'Known data'),
                    ClientInfo('American Express', 'Enterprise Client', 'Financial Services', 'Customer service platform', 'Known data'),
                    ClientInfo('Spotify', 'Enterprise Client', 'Technology', 'Customer relationship management', 'Known data')
                ],
                'segments': [
                    CustomerSegment('Enterprise', 'Large corporations', ['Sales teams', 'Customer service'], 'Large', 'Known data'),
                    CustomerSegment('SMB', 'Small and medium businesses', ['Sales Cloud Essentials'], 'Medium', 'Known data')
                ]
            }
        }
        
        company_key = company_name.lower().strip()
        if company_key in company_data:
            return company_data[company_key]['clients'], company_data[company_key]['segments']
        
        return fallback_clients, fallback_segments
    def search_sec_filings(self, company_name: str) -> List[Dict]:
        """Search SEC EDGAR database for company filings (free)"""
        try:
            # SEC EDGAR API
            search_url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=&type=10-K&dateb=&owner=include&count=10&search_text={quote(company_name)}"
            
            # Note: This is a simplified example. Real implementation would parse SEC data
            # For now, return placeholder that indicates where SEC data would go
            return [{
                'title': f'SEC Filing search for {company_name}',
                'url': search_url,
                'snippet': 'SEC filings may contain client information in 10-K reports'
            }]
            
        except Exception as e:
            print(f"SEC search error: {e}")
        
        return []
    
    def search_news_api(self, query: str) -> List[Dict]:
        """Search for news using NewsAPI.org (free tier: 100 requests/day)"""
        try:
            # You need to register for free at https://newsapi.org/
            # api_key = "YOUR_FREE_NEWSAPI_KEY"  # Uncomment and add your key
            
            # For demo purposes, using a placeholder
            # In real implementation, uncomment below:
            """
            url = f"https://newsapi.org/v2/everything?q={quote(query)}&apiKey={api_key}&pageSize=10"
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                results = []
                for article in data.get('articles', []):
                    results.append({
                        'title': article.get('title', ''),
                        'url': article.get('url', ''),
                        'snippet': article.get('description', '')
                    })
                return results
            """
            
            # Placeholder for now
            return [{
                'title': f'News search for {query}',
                'url': 'https://newsapi.org',
                'snippet': 'Register for free NewsAPI key to get real news results'
            }]
            
        except Exception as e:
            print(f"News API error: {e}")
        
        return []
    
    def scrape_company_website(self, company_name: str) -> List[Dict]:
        """Attempt to find and scrape company website"""
        try:
            # Simple approach: try common website patterns
            possible_urls = [
                f"https://www.{company_name.lower().replace(' ', '')}.com",
                f"https://{company_name.lower().replace(' ', '')}.com",
                f"https://www.{company_name.lower().replace(' ', '')}.net",
                f"https://{company_name.lower().replace(' ', '')}.org"
            ]
            
            for url in possible_urls:
                try:
                    req = urllib.request.Request(url, headers=self.headers)
                    response = urllib.request.urlopen(req, timeout=10)
                    html = response.read().decode('utf-8')
                    
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Extract text from common sections
                    text_content = ""
                    for tag in soup.find_all(['p', 'div', 'span', 'h1', 'h2', 'h3']):
                        text_content += tag.get_text() + " "
                    
                    return [{
                        'title': f'{company_name} Official Website',
                        'url': url,
                        'snippet': text_content[:1000] + "..." if len(text_content) > 1000 else text_content
                    }]
                    
                except:
                    continue
            
        except Exception as e:
            print(f"Website scraping error: {e}")
        
        return []
    
    def extract_clients_from_text(self, text: str, company_name: str) -> List[ClientInfo]:
        """Enhanced client extraction with better patterns"""
        clients = []
        
        # More comprehensive patterns for client mentions
        patterns = [
            r'(?:major\s+)?(?:clients?|customers?|partners?)\s+(?:include|are|such as|like)[\s:]*([A-Z][a-zA-Z\s&.,Inc-]+?)(?:\s*[,;.]|$)',
            r'(?:works?\s+with|serves?|partnered?\s+with|clients?\s+include)\s+([A-Z][a-zA-Z\s&.,Inc-]+?)(?:\s*[,;.]|$)',
            r'(?:case\s+studies?|success\s+stories?)\s+.*?([A-Z][a-zA-Z\s&.,Inc-]{3,30})(?:\s*[,;.]|$)',
            r'([A-Z][a-zA-Z\s&.,Inc-]{3,30})\s+(?:uses?|chose|selected|implemented|deployed)',
            r'(?:partnership|collaboration|alliance)\s+with\s+([A-Z][a-zA-Z\s&.,Inc-]+?)(?:\s*[,;.]|$)'
        ]
        
        # Known company suffixes to help identify real companies
        company_suffixes = ['Inc', 'Corp', 'Corporation', 'LLC', 'Ltd', 'Limited', 'Co', 'Company']
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                client_name = match.strip(' .,;:')
                
                # Filter out common false positives
                if (len(client_name) > 3 and 
                    client_name.lower() != company_name.lower() and
                    not client_name.lower() in ['the', 'and', 'with', 'our', 'all', 'more', 'other'] and
                    len(client_name) < 50):
                    
                    # Determine relationship type based on context
                    relationship_type = "Client/Customer"
                    if 'partner' in text.lower():
                        relationship_type = "Business Partner"
                    elif 'case study' in text.lower():
                        relationship_type = "Case Study Client"
                    
                    clients.append(ClientInfo(
                        name=client_name,
                        relationship_type=relationship_type,
                        industry="Unknown",
                        description=f"Mentioned in context: {text[:100]}...",
                        source="Web search"
                    ))
        
        return clients
    
    def extract_segments_from_text(self, text: str) -> List[CustomerSegment]:
        """Enhanced segment extraction"""
        segments = []
        
        # More specific segment patterns
        segment_patterns = {
            'Enterprise': ['enterprise', 'large enterprise', 'fortune 500', 'big business'],
            'SMB': ['small business', 'SMB', 'small to medium', 'mid-market', 'middle market'],
            'Startups': ['startup', 'start-up', 'emerging companies', 'early stage'],
            'Government': ['government', 'public sector', 'federal', 'municipal'],
            'Healthcare': ['healthcare', 'hospitals', 'medical', 'pharma'],
            'Financial Services': ['banks', 'financial', 'fintech', 'insurance'],
            'Technology': ['tech companies', 'software', 'SaaS', 'IT'],
            'Manufacturing': ['manufacturing', 'industrial', 'factory'],
            'Retail': ['retail', 'e-commerce', 'merchants', 'stores'],
            'Education': ['education', 'schools', 'universities', 'academic']
        }
        
        text_lower = text.lower()
        
        for segment_name, keywords in segment_patterns.items():
            for keyword in keywords:
                if keyword in text_lower:
                    segments.append(CustomerSegment(
                        segment_name=segment_name,
                        description=f"Serves {segment_name.lower()} sector",
                        characteristics=[f"Keyword: {keyword}"],
                        size_estimate="Unknown",
                        source="Web analysis"
                    ))
                    break  # Only add each segment once
        
        return segments
    
    def research_company_clients(self, company_name: str) -> ResearchResult:
        """Main research function using free resources"""
        print(f"🔍 Starting client research for: {company_name}")
        print("Using free resources: DuckDuckGo, Wikipedia, Website scraping...")
        
        all_clients = []
        all_segments = []
        industry_focus = []
        business_model = "Unknown"
        target_markets = []
        
        # 1. Wikipedia search
        print("📚 Searching Wikipedia...")
        wiki_results = self.search_wikipedia(company_name)
        for result in wiki_results:
            content = result.get('snippet', '') + ' ' + result.get('title', '')
            all_clients.extend(self.extract_clients_from_text(content, company_name))
            all_segments.extend(self.extract_segments_from_text(content))
        time.sleep(self.delay)
        
        # 2. Company website scraping
        print("🌐 Attempting to scrape company website...")
        website_results = self.scrape_company_website(company_name)
        for result in website_results:
            content = result.get('snippet', '')
            all_clients.extend(self.extract_clients_from_text(content, company_name))
            all_segments.extend(self.extract_segments_from_text(content))
        time.sleep(self.delay)
        
        # 3. DuckDuckGo searches
        search_queries = [
            f'"{company_name}" clients customers list',
            f'"{company_name}" case studies success stories',
            f'"{company_name}" partnerships collaborations',
            f'"{company_name}" serves industries sectors',
            f'"{company_name}" target market customer base'
        ]
        
        for query in search_queries:
            print(f"🔍 Searching: {query}")
            results = self.search_duckduckgo(query, num_results=5)
            
            for result in results:
                content = result.get('snippet', '') + ' ' + result.get('title', '')
                all_clients.extend(self.extract_clients_from_text(content, company_name))
                all_segments.extend(self.extract_segments_from_text(content))
            
            time.sleep(self.delay)
        
        # 4. SEC filings (placeholder)
        print("🏛️ Checking SEC filings...")
        sec_results = self.search_sec_filings(company_name)
        # SEC parsing would go here
        
        # 5. Add fallback data if we didn't find much
        if len(all_clients) == 0 and len(all_segments) <= 1:
            print("📋 Adding known data for common companies...")
            fallback_clients, fallback_segments = self.add_fallback_data(company_name)
            all_clients.extend(fallback_clients)
            all_segments.extend(fallback_segments)
        
        # Remove duplicates
        unique_clients = []
        seen_clients = set()
        for client in all_clients:
            client_key = client.name.lower().strip()
            if client_key not in seen_clients and len(client_key) > 2:
                unique_clients.append(client)
                seen_clients.add(client_key)
        
        unique_segments = []
        seen_segments = set()
        for segment in all_segments:
            if segment.segment_name not in seen_segments:
                unique_segments.append(segment)
                seen_segments.add(segment.segment_name)
        
        print(f"✅ Research complete! Found {len(unique_clients)} potential clients and {len(unique_segments)} customer segments")
        
        return ResearchResult(
            company_name=company_name,
            major_clients=unique_clients,
            customer_segments=unique_segments,
            industry_focus=industry_focus,
            business_model=business_model,
            target_markets=target_markets,
            research_timestamp=datetime.now().isoformat()
        )
    
    def export_to_csv(self, result: ResearchResult, filename: str = None):
        """Export research results to CSV"""
        if filename is None:
            filename = f"{result.company_name}_client_research_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        # Clean filename
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write header
            writer.writerow(['Company', 'Research Type', 'Name', 'Type', 'Industry', 'Description', 'Source'])
            
            # Write clients
            for client in result.major_clients:
                writer.writerow([
                    result.company_name,
                    'Major Client',
                    client.name,
                    client.relationship_type,
                    client.industry,
                    client.description[:200] + "..." if len(client.description) > 200 else client.description,
                    client.source
                ])
            
            # Write segments
            for segment in result.customer_segments:
                writer.writerow([
                    result.company_name,
                    'Customer Segment',
                    segment.segment_name,
                    'Segment',
                    'N/A',
                    segment.description,
                    segment.source
                ])
        
        print(f"📊 Results exported to: {filename}")
    
    def display_results(self, result: ResearchResult):
        """Display research results in a formatted way"""
        print("\n" + "="*70)
        print(f"📋 CLIENT RESEARCH REPORT: {result.company_name}")
        print("="*70)
        
        print(f"🕐 Research conducted on: {result.research_timestamp}")
        print(f"📊 Data sources: DuckDuckGo, Wikipedia, Website scraping")
        
        print(f"\n🏢 POTENTIAL MAJOR CLIENTS ({len(result.major_clients)} found):")
        print("-" * 50)
        if result.major_clients:
            for i, client in enumerate(result.major_clients, 1):
                print(f"{i}. {client.name}")
                print(f"   🤝 Relationship: {client.relationship_type}")
                print(f"   🏭 Industry: {client.industry}")
                print(f"   📝 Context: {client.description[:100]}...")
                print(f"   📍 Source: {client.source}")
                print()
        else:
            print("❌ No major clients identified from available free sources.")
            print("💡 Tip: Try searching for company case studies or press releases manually.")
        
        print(f"\n🎯 CUSTOMER SEGMENTS ({len(result.customer_segments)} found):")
        print("-" * 50)
        if result.customer_segments:
            for i, segment in enumerate(result.customer_segments, 1):
                print(f"{i}. {segment.segment_name}")
                print(f"   📄 Description: {segment.description}")
                print(f"   🔍 Evidence: {', '.join(segment.characteristics)}")
                print(f"   📈 Size: {segment.size_estimate}")
                print(f"   📍 Source: {segment.source}")
                print()
        else:
            print("❌ No customer segments clearly identified.")
            print("💡 Tip: Check the company's 'About' page or investor relations for target market info.")
        
        print(f"\n📈 BUSINESS INSIGHTS:")
        print("-" * 30)
        print(f"🏢 Business Model: {result.business_model}")
        print(f"🎯 Target Markets: {', '.join(result.target_markets) if result.target_markets else 'Not clearly identified'}")
        print(f"🏭 Industry Focus: {', '.join(result.industry_focus) if result.industry_focus else 'Not clearly identified'}")
        
        print(f"\n💡 RESEARCH NOTES:")
        print("-" * 20)
        print("• This research uses free resources and may have limited coverage")
        print("• Consider manual verification of identified clients")
        print("• Check company's LinkedIn, press releases, and investor materials")
        print("• SEC filings (10-K forms) often contain detailed client information")

def main():
    """Main function to run the client research tool"""
    print("🔍 FREE CLIENT RESEARCH TOOL")
    print("=" * 35)
    print("Uses: DuckDuckGo, Wikipedia, Website scraping")
    print("=" * 35)
    
    # Get company name from user
    company_name = input("Enter company name: ").strip()
    
    if not company_name:
        print("❌ Please provide a valid company name.")
        return
    
    # Initialize the research tool
    researcher = ClientResearchTool(delay_between_requests=2)
    
    # Conduct research
    try:
        result = researcher.research_company_clients(company_name)
        
        # Display results
        researcher.display_results(result)
        
        # Ask if user wants to export
        export = input("\n💾 Export results to CSV? (y/n): ").lower()
        if export == 'y':
            researcher.export_to_csv(result)
        
        print("\n🎉 Research complete!")
        print("\n💡 Pro tips for better results:")
        print("• Try searching '[company] case studies' manually")
        print("• Check the company's LinkedIn page")
        print("• Look for press releases and news articles")
        print("• Review SEC filings for public companies")
        
    except Exception as e:
        print(f"❌ Error during research: {str(e)}")
        print("💡 Try checking your internet connection or the company name spelling")

if __name__ == "__main__":
    main()