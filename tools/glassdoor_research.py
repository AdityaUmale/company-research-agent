import requests
import sys

RAPIDAPI_KEY = "da887e29a6mshf393f769af15600p1b62bbjsn1857ffd9b6fc"
HOST = "real-time-glassdoor-data.p.rapidapi.com"
HEADERS = {
    "x-rapidapi-host": HOST,
    "x-rapidapi-key": RAPIDAPI_KEY
}


def get_company_id(company_name):
    """Search for company ID using the company name."""
    url = f"https://{HOST}/company-search"
    params = {
        "query": company_name,
        "limit": 1,
        "domain": "www.glassdoor.com"
    }
    response = requests.get(url, headers=HEADERS, params=params)

    if response.status_code == 200:
        data = response.json().get("data", [])
        if data:
            company = data[0]
            print(f"✅ Found company: {company['name']} (ID: {company['company_id']})")
            return company['company_id']
        else:
            print(f"❌ No results found for '{company_name}'")
            return None
    else:
        print(f"❌ Failed to search company. Status: {response.status_code}")
        print(response.text)
        return None


def get_reviews(company_id, page=1):
    """Fetch company reviews given its ID."""
    url = f"https://{HOST}/company-reviews"
    params = {
        "company_id": company_id,
        "page": page,
        "sort": "POPULAR",
        "language": "en",
        "only_current_employees": "false",
        "extended_rating_data": "false",
        "domain": "www.glassdoor.com"
    }
    response = requests.get(url, headers=HEADERS, params=params)

    if response.status_code == 200:
        reviews = response.json().get("data", {}).get("reviews", [])
        if not reviews:
            print("⚠️ No reviews found.")
            return
        for idx, review in enumerate(reviews, 1):
            print(f"\n--- Review {idx} ---")
            print(f"Summary   : {review.get('summary')}")
            print(f"Rating    : {review.get('rating')}")
            print(f"Job Title : {review.get('job_title')}")
            print(f"Pros      : {review.get('pros')}")
            print(f"Cons      : {review.get('cons')}")
            print(f"Link      : {review.get('review_link')}")
    else:
        print(f"❌ Failed to fetch reviews. Status: {response.status_code}")
        print(response.text)


def get_glassdoor_summary(company_name, max_reviews=5):
    """Return a structured summary of Glassdoor reviews for a company."""
    company_id = get_company_id(company_name)
    if not company_id:
        return {"reviews": [], "error": f"No Glassdoor company found for '{company_name}'"}
    url = f"https://{HOST}/company-reviews"
    params = {
        "company_id": company_id,
        "page": 1,
        "sort": "POPULAR",
        "language": "en",
        "only_current_employees": "false",
        "extended_rating_data": "false",
        "domain": "www.glassdoor.com"
    }
    response = requests.get(url, headers=HEADERS, params=params)
    if response.status_code == 200:
        reviews = response.json().get("data", {}).get("reviews", [])
        summary = []
        for review in reviews[:max_reviews]:
            summary.append({
                "summary": review.get("summary"),
                "rating": review.get("rating"),
                "job_title": review.get("job_title"),
                "pros": review.get("pros"),
                "cons": review.get("cons"),
                "link": review.get("review_link")
            })
        return {"reviews": summary, "company_id": company_id}
    else:
        return {"reviews": [], "error": f"Failed to fetch reviews. Status: {response.status_code}"}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python glassdoor_research.py <company_name>")
        sys.exit(1)

    company_name = sys.argv[1]
    company_id = get_company_id(company_name)
    if company_id:
        get_reviews(company_id)
