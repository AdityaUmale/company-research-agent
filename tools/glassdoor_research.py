import requests
from bs4 import BeautifulSoup
import pandas as pd

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

def get_jobs(company):
    all_jobs = []
    all_jobs += scrape_simplyhired(company)
    all_jobs += scrape_remoteok(company)
    all_jobs += scrape_weworkremotely(company)
    return pd.DataFrame(all_jobs)

if __name__ == "__main__":
    import sys
    company_input = sys.argv[1] if len(sys.argv) > 1 else input("Enter company name: ")

    df = get_jobs(company_input)
    if df.empty:
        print("No jobs found.")
    else:
        print(df)
        df.to_csv(f"{company_input}_jobs.csv", index=False)
        print(f"\nSaved to {company_input}_jobs.csv")
