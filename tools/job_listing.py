import requests
from bs4 import BeautifulSoup
import pandas as pd

# 🔐 Set your JSearch RapidAPI key here
RAPIDAPI_KEY = "da887e29a6mshf393f769af15600p1b62bbjsn1857ffd9b6fc"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def scrape_simplyhired(company):
    print("[*] Scraping SimplyHired...")
    url = f"https://www.simplyhired.com/search?q={company.replace(' ', '+')}"
    resp = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(resp.text, "html.parser")
    jobs = []

    for card in soup.select("div.card-content"):
        title_el = card.select_one("a")
        loc_el = card.select_one("span.jobposting-location")
        if title_el and loc_el:
            title = title_el.get_text(strip=True)
            location = loc_el.get_text(strip=True)
            if company.lower() in title.lower():
                jobs.append({
                    "title": title,
                    "location": location,
                    "source": "SimplyHired"
                })

    return jobs


def scrape_remoteok(company):
    print("[*] Scraping RemoteOK...")
    url = "https://remoteok.com/remote-jobs"
    resp = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(resp.text, "html.parser")
    jobs = []

    for row in soup.select("tr.job"):
        title_el = row.select_one("h2")
        company_el = row.select_one("h3")
        if title_el and company_el:
            title = title_el.get_text(strip=True)
            company_name = company_el.get_text(strip=True)
            if company.lower() in company_name.lower() or company.lower() in title.lower():
                jobs.append({
                    "title": title,
                    "location": "Remote",
                    "source": "RemoteOK"
                })

    return jobs


def scrape_weworkremotely(company):
    print("[*] Scraping WeWorkRemotely...")
    url = "https://weworkremotely.com/remote-jobs"
    resp = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(resp.text, "html.parser")
    jobs = []

    for section in soup.select("section.jobs"):
        for li in section.select("li"):
            company_el = li.select_one("span.company")
            title_el = li.select_one("span.title")
            if company_el and title_el:
                company_name = company_el.get_text(strip=True)
                title = title_el.get_text(strip=True)
                if company.lower() in company_name.lower() or company.lower() in title.lower():
                    jobs.append({
                        "title": title,
                        "location": "Remote",
                        "source": "WeWorkRemotely"
                    })

    return jobs


def scrape_jsearch(company, api_key):
    print("[*] Scraping JSearch API...")
    url = "https://jsearch.p.rapidapi.com/search"

    querystring = {
        "query": company,
        "page": "1",
        "num_pages": "1"
    }

    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
    }

    response = requests.get(url, headers=headers, params=querystring)
    jobs = []

    if response.status_code == 200:
        data = response.json()
        for job in data.get("data", []):
            jobs.append({
                "title": job.get("job_title"),
                "location": job.get("job_city") or job.get("job_country") or "N/A",
                "source": "JSearchAPI",
                "company": job.get("employer_name"),
                "url": job.get("job_apply_link"),
                "job_type": job.get("job_employment_type")
            })
    else:
        print(f"[!] JSearch API error: {response.status_code} - {response.text}")

    return jobs


def get_jobs(company):
    all_jobs = []
    all_jobs += scrape_simplyhired(company)
    all_jobs += scrape_remoteok(company)
    all_jobs += scrape_weworkremotely(company)
    all_jobs += scrape_jsearch(company, RAPIDAPI_KEY)
    return pd.DataFrame(all_jobs)


if __name__ == "__main__":
    import sys

    company_input = sys.argv[1] if len(sys.argv) > 1 else input("Enter company name: ").strip()
    df = get_jobs(company_input)

    if df.empty:
        print("No jobs found.")
    else:
        print(df)
        df.to_csv(f"{company_input}_jobs.csv", index=False)
        print(f"\n✅ Saved to {company_input}_jobs.csv")
