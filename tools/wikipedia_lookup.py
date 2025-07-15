# tools/wikipedia_lookup.py
import wikipedia

def get_company_wikipedia_summary(company_name):
    try:
        wikipedia.set_lang("en")
        page = wikipedia.page(company_name)
        summary = wikipedia.summary(company_name, sentences=5)
        return {
            "name": company_name,
            "summary": summary,
            "url": page.url,
            "title": page.title,
            "confidence_score": 0.85  # Tuned based on source reliability
        }
    except Exception as e:
        print(f"[Wikipedia] Error fetching data: {e}")
        return None
