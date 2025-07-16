# Company Research Agent

## Overview
The Company Research Agent is a Python-based tool that aggregates, analyzes, and synthesizes data from multiple sources to generate a comprehensive, professional markdown report about any company. It is designed for recruiters, analysts, and business professionals who need a quick, reliable, and detailed company profile.

## Features
- Aggregates data from:
  - Company overview (Wikipedia, official site, LinkedIn)
    
    ![Company Overview Tool](images/Company%20Overview%20Tool%20-%20visual%20selection.png)
  - Financials (public/private, yfinance, Alpha Vantage)
    
    ![Financial Snapshot Tool](images/financial%C2%A0snapshot%20tool%20-%20visual%20selection.png)
  - News (NewsAPI, sentiment, controversies, future plans)
    
    ![News Tool](images/news%20tool%20-%20visual%20selection.png)
  - Social media (LinkedIn, Twitter, Instagram, YouTube)
    
    ![Social Media Research Tool](images/social%20media%20research%20tool%20-%20visual%20selection.png)
  - Competitors (SimilarWeb API)
    
    ![Competitor Analysis Tool](images/competitor%20analysis%C2%A0tool%20-%20visual%20selection.png)
  - Customers/clients (web search, Wikipedia, DuckDuckGo)
    
    ![Customer Research Tool](images/customer%C2%A0research%C2%A0tool%20-%20visual%20selection.png)
  - Glassdoor reviews (RapidAPI)
    
    ![Glassdoor Research Tool](images/Glassdoor%C2%A0research%20tool%20-%20visual%20selection.png)
  - Job listings (multiple job boards, JSearch API)
    
    ![Job Listing Tool](images/job%C2%A0listing%20tool%20-%20visual%20selection.png)




## Technical Flow
1. **Parse CLI Arguments** (company name, email)
2. **Initialize Researcher** (LLM models, config)
3. **Collect Raw Data** (call each tool: overview, financials, news, social, competitors, customers, glassdoor, jobs)
4. **Calculate Confidence Scores** (for each section)
5. **Run LLM Mini Analysis** (news, glassdoor)
6. **Run LLM Premium Analysis** (final summary/insights)
7. **Debug Print** (full research data)
8. **Generate Markdown Report** (write all sections to file)
9. **Generate JSON Output** (save all data and analysis)

## Setup Instructions
1. **Clone the repository:**
   ```bash
   git clone <repo-url>
   cd company-research-agent
   ```
2. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Set up API keys:**
   - Create a `.env` file in the project root with your OpenAI API key:
     ```
     OPENAI_API_KEY=your_openai_key_here
     ```
   - (Optional) Add other API keys (NewsAPI, Alpha Vantage, RapidAPI) as needed in the respective tool files.

## Usage
### Run the Main Pipeline
```bash
python main.py --company "Google" --email "your_email@example.com"
```
- Generates `google_report.md` and `google_data.json` in the project directory.

### Run Individual Tools
- **News:**
  ```bash
  python tools/news.py --company "Google" --email "your_email@example.com"
  ```
- **Company Overview:**
  ```bash
  python tools/company_overview.py
  ```
- **Financial Snapshot:**
  ```bash
  python tools/financial_snapshot.py
  ```
- **Competitor Analysis:**
  ```bash
  python tools/competitor_analysis.py
  ```
- **Customer Research:**
  ```bash
  python tools/customer_research.py
  ```
- **Glassdoor Research:**
  ```bash
  python tools/glassdoor_research.py "Google"
  ```
- **Job Listings:**
  ```bash
  python tools/job_listing.py "Google"
  ```
- **Social Media Research:**
  ```bash
  python tools/social_media_research.py
  ```

## Tool Descriptions
- **main.py:** Orchestrates the full research pipeline and report generation.
- **tools/company_overview.py:** Gathers company basics from Wikipedia, official site, LinkedIn.
- **tools/financial_snapshot.py:** Fetches public/private financials, estimates, and ratios.
- **tools/news.py:** Collects and analyzes recent news, sentiment, controversies, future plans.
- **tools/social_media_research.py:** Scrapes LinkedIn, Twitter, Instagram, YouTube for presence and stats.
- **tools/competitor_analysis.py:** Gets direct competitors and their metrics from SimilarWeb API.
- **tools/customer_research.py:** Finds major clients and customer segments from web and Wikipedia.
- **tools/glassdoor_research.py:** Fetches and summarizes employee reviews from Glassdoor.
- **tools/job_listing.py:** Aggregates job postings from multiple boards and APIs.

## Customization
- Adjust the number of news articles, job listings, or competitors in `main.py` as needed.
- Add or update API keys in the respective tool files.
- Modify report formatting in `main.py` for your preferred style.

## Troubleshooting
- **Missing Data:** Some sections may be empty if public data is unavailable or API limits are reached.
- **API Errors:** Ensure all required API keys are set and valid.
- **Rate Limits:** Some APIs (NewsAPI, RapidAPI) have daily limits; consider upgrading or rotating keys.
- **Selenium Issues:** For social media scraping, install ChromeDriver and ensure it matches your Chrome version.
- **Encoding Issues:** Use UTF-8 encoding for all files and terminal output.

## License
MIT License

---
*For questions or contributions, please open an issue or pull request on GitHub.* 