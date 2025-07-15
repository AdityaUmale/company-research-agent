# test_scraper.py

from tools.website_scraper import scrape_company_about

def test_scrape_about():
    company_url = "https://www.tesla.com"  # You can try others too
    result = scrape_company_about(company_url)

    if result:
        print("✅ About Page Scraped!")
        print("URL:", result["about_page_url"])
        print("Excerpt:", result["content_excerpt"])
        print("Confidence:", result["confidence_score"])
    else:
        print("❌ Failed to scrape company about page.")

if __name__ == "__main__":
    test_scrape_about()
