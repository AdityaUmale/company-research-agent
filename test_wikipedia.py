# test_wikipedia.py

from tools.wikipedia_lookup import get_company_wikipedia_summary

def test_wiki_summary():
    company = "Tesla, Inc."
    result = get_company_wikipedia_summary(company)
    
    if result:
        print("✅ Wikipedia Summary Retrieved!")
        print("Title:", result["title"])
        print("Summary:", result["summary"])
        print("URL:", result["url"])
        print("Confidence:", result["confidence_score"])
    else:
        print("❌ No summary found.")

if __name__ == "__main__":
    test_wiki_summary()
