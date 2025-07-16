import requests
import warnings
from urllib3.exceptions import NotOpenSSLWarning

# Suppress the OpenSSL warning
warnings.filterwarnings("ignore", category=NotOpenSSLWarning)

headers = {
    "x-rapidapi-host": "similarweb12.p.rapidapi.com",
    "x-rapidapi-key": "da887e29a6mshf393f769af15600p1b62bbjsn1857ffd9b6fc"
}

def fetch_company_competitors(domain):
    url = f"https://similarweb12.p.rapidapi.com/v2/company-details?company_domain={domain}"
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        competitors = data.get("competitors", {}).get(domain)
        if not competitors:
            print("❌ No competitors found.")
            return

        print(f"✅ Top competitors for {domain}:\n")
        for i, comp in enumerate(competitors, 1):
            name = comp.get("name", "N/A")
            domain = comp.get("domain", "N/A")
            employees_min = comp.get("employeesMin")
            employees_max = comp.get("employeesMax")
            revenue_min = comp.get("revenueMin")
            revenue_max = comp.get("revenueMax")
            total_visits = comp.get("totalVisits")
            hq_city = comp.get("headquarterCity") or "N/A"
            hq_country = comp.get("headquarterCountryCode") or "N/A"
            icon = comp.get("icon", "N/A")

            print(f"{i}. {name} ({domain})")
            print(f"   🧑 Employees: {employees_min or 'N/A'}–{employees_max or 'N/A'}")

            if revenue_min is not None and revenue_max is not None:
                print(f"   💰 Revenue: {revenue_min:,}–{revenue_max:,}")
            else:
                print(f"   💰 Revenue: N/A")

            if total_visits:
                print(f"   🌍 Visits: {int(total_visits):,}")
            else:
                print(f"   🌍 Visits: N/A")

            print(f"   🏢 HQ: {hq_city}, {hq_country}")
            print(f"   🖼 Icon: {icon}\n")

    except requests.exceptions.HTTPError as err:
        print(f"❌ HTTP error: {err}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    domain_input = input("Enter company domain (e.g., rapidapi.com): ").strip().lower()
    fetch_company_competitors(domain_input)
