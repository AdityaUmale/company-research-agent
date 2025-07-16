import argparse
import json
import os
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser
from langchain.schema import HumanMessage, SystemMessage
from langchain.callbacks import get_openai_callback
from dotenv import load_dotenv
import re
from dataclasses import asdict, is_dataclass
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
import asyncio
from functools import lru_cache
import pprint
import difflib
import wikipedia

from tools.company_overview import research_company_overview
from tools.financial_snapshot import FinancialSnapshot
from tools.news import research_company_news, analyze_news_sentiment, detect_controversies, extract_future_plans, structure_research_data
from tools.social_media_research import SocialMediaResearcher
from tools.competitor_analysis import get_competitor_summary
from tools.customer_research import ClientResearchTool
from tools.glassdoor_research import get_glassdoor_summary
from tools.job_listing import get_job_listings

def dataclass_to_dict(obj: Any) -> Any:
    """Recursively converts dataclass instances (and lists/dicts of them) to dicts."""
    if is_dataclass(obj):
        return {field: dataclass_to_dict(getattr(obj, field)) for field in obj.__dataclass_fields__}
    elif isinstance(obj, dict):
        return {k: dataclass_to_dict(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [dataclass_to_dict(item) for item in obj]
    else:
        return obj

def summarize_list(data: List[Dict]) -> List[Dict]:
    """Summarizes a list of dictionaries by taking the first non-null value for each key."""
    if not data:
        return []
    summary = []
    for item in data:
        if not isinstance(item, dict):
            summary.append(item)
            continue
        summary_item = {}
        for key in item:
            if item[key] is not None and item[key] != "":
                summary_item[key] = item[key]
        summary.append(summary_item)
    return summary

class CompanyAnalysis(BaseModel):
    """Structured output for company analysis"""
    executive_summary: str = Field(description="3-4 sentence executive summary for recruiters")
    key_insights: List[str] = Field(description="Top 5 key insights for recruiters")
    missing_data_assessment: str = Field(description="Assessment of what critical data is missing")
    confidence_rationale: str = Field(description="Why the confidence scores are what they are")

class NewsAnalysis(BaseModel):
    """Structured output for news analysis"""
    sentiment_score: float = Field(description="Overall sentiment score -1 to 1")
    controversy_level: str = Field(description="LOW, MEDIUM, or HIGH")
    key_themes: List[str] = Field(description="Top 3-5 themes from news")
    recruiter_concerns: List[str] = Field(description="Specific concerns for recruiters")

class GlassdoorAnalysis(BaseModel):
    """Structured output for Glassdoor analysis"""
    overall_sentiment: str = Field(description="POSITIVE, NEUTRAL, or NEGATIVE")
    top_pros: List[str] = Field(description="Top 3 pros mentioned")
    top_cons: List[str] = Field(description="Top 3 cons mentioned")
    recruiter_notes: List[str] = Field(description="Key notes for recruiters")

class TokenOptimizedResearcher:
    def __init__(self, openai_api_key: str):
        self.llm_mini = ChatOpenAI(
            temperature=0, 
            model="gpt-4o-mini"
        )
        self.llm_premium = ChatOpenAI(
            temperature=0, 
            model="gpt-4o"
        )
        self.total_tokens = 0
        
    def clean_company_name(self, company_name: str) -> str:
        """Clean company name for filename usage"""
        return re.sub(r'[^\w\s-]', '', company_name).strip().replace(' ', '_')

    @lru_cache(maxsize=128)
    def calculate_confidence_score(self, data_str: str) -> float:
        """Cached confidence calculation to avoid repeated processing"""
        if not data_str or data_str == "null":
            return 0.0
        
        try:
            data = json.loads(data_str)
            if isinstance(data, dict):
                non_empty = sum(1 for v in data.values() if v and v != "Not available" and v != "N/A")
                return round(non_empty / len(data) if data else 0.0, 2)
            elif isinstance(data, list):
                return 0.8 if data else 0.0
            return 0.6 if data else 0.0
        except:
            return 0.3

    def analyze_news_efficiently(self, news_data: Dict) -> NewsAnalysis:
        """Analyze news data with single optimized LLM call, with fallback to sentiment_summary and controversies if needed."""
        if not news_data or not news_data.get('key_articles'):
            # Fallback: try to use sentiment_summary and controversies
            sentiment_score = 0.0
            controversy_level = "LOW"
            key_themes = []
            recruiter_concerns = []
            # Fallback for sentiment
            sentiment_summary = news_data.get('sentiment_summary', {})
            if sentiment_summary:
                pos = sentiment_summary.get('positive', 0)
                neg = sentiment_summary.get('negative', 0)
                total = sentiment_summary.get('total', 0)
                if total > 0:
                    sentiment_score = round((pos - neg) / total, 2)
            # Fallback for controversy
            controversies = news_data.get('controversies', [])
            if controversies:
                if len(controversies) > 3:
                    controversy_level = "HIGH"
                else:
                    controversy_level = "MEDIUM"
            return NewsAnalysis(
                sentiment_score=sentiment_score,
                controversy_level=controversy_level,
                key_themes=key_themes,
                recruiter_concerns=recruiter_concerns
            )
        
        # Truncate data to save tokens
        articles = news_data.get('key_articles', [])[:5]  # Only analyze top 5
        
        parser = PydanticOutputParser(pydantic_object=NewsAnalysis)
        
        prompt = PromptTemplate(
            template="""Analyze this news data for recruiting purposes:
Articles: {articles}
Positive: {positive}
Negative: {negative}

{format_instructions}

Focus on: recruitment impact, company reputation, stability concerns.""",
            input_variables=["articles", "positive", "negative"],
            partial_variables={"format_instructions": parser.get_format_instructions()}
        )
        
        with get_openai_callback() as cb:
            response = self.llm_mini.invoke(prompt.format(
                articles=str(articles)[:1000],  # Truncate to 1000 chars
                positive=str(news_data.get('recent_positive_news', []))[:500],
                negative=str(news_data.get('recent_negative_news', []))[:500]
            ))
            self.total_tokens += cb.total_tokens
        
        try:
            content = response.content
            if not isinstance(content, str):
                content = str(content)
            return parser.parse(content)
        except:
            return NewsAnalysis(
                sentiment_score=0.0,
                controversy_level="MEDIUM",
                key_themes=["Analysis failed"],
                recruiter_concerns=["Unable to analyze news sentiment"]
            )

    def analyze_glassdoor_efficiently(self, glassdoor_data: List) -> GlassdoorAnalysis:
        """Analyze Glassdoor data with single optimized LLM call"""
        if not glassdoor_data:
            return GlassdoorAnalysis(
                overall_sentiment="NEUTRAL",
                top_pros=[],
                top_cons=[],
                recruiter_notes=["No Glassdoor data available"]
            )
        
        # Sample only recent reviews to save tokens
        sample_reviews = glassdoor_data[:3]
        
        parser = PydanticOutputParser(pydantic_object=GlassdoorAnalysis)
        
        prompt = PromptTemplate(
            template="""Analyze these employee reviews for recruiting insights:
Reviews: {reviews}

{format_instructions}

Focus on: common themes, work culture, management quality, career growth.""",
            input_variables=["reviews"],
            partial_variables={"format_instructions": parser.get_format_instructions()}
        )
        
        with get_openai_callback() as cb:
            response = self.llm_mini.invoke(prompt.format(
                reviews=str(sample_reviews)[:1500]  # Truncate to save tokens
            ))
            self.total_tokens += cb.total_tokens
        
        try:
            content = response.content
            if not isinstance(content, str):
                content = str(content)
            return parser.parse(content)
        except:
            return GlassdoorAnalysis(
                overall_sentiment="NEUTRAL",
                top_pros=["Unable to analyze"],
                top_cons=["Unable to analyze"],
                recruiter_notes=["Glassdoor analysis failed"]
            )

    def generate_final_analysis(self, company_name: str, all_data: Dict) -> CompanyAnalysis:
        """Single comprehensive analysis call - use premium model here"""
        
        # Create condensed summary of all data
        condensed_data = {
            "overview": {
                "founded": all_data.get('overview', {}).get('data', {}).get('founded', 'N/A'),
                "employees": all_data.get('overview', {}).get('data', {}).get('employee_count', 'N/A'),
                "hq": all_data.get('overview', {}).get('data', {}).get('headquarters', 'N/A'),
                "confidence": all_data.get('overview', {}).get('confidence', 0)
            },
            "financials": {
                "revenue": all_data.get('financials', {}).get('data', {}).get('financial_data', {}).get('estimated_revenue', 'N/A'),
                "confidence": all_data.get('financials', {}).get('confidence', 0)
            },
            "news_sentiment": all_data.get('news_analysis', {}).sentiment_score if hasattr(all_data.get('news_analysis', {}), 'sentiment_score') else 0,
            "glassdoor_sentiment": all_data.get('glassdoor_analysis', {}).overall_sentiment if hasattr(all_data.get('glassdoor_analysis', {}), 'overall_sentiment') else 'NEUTRAL',
            "competitors_count": len(all_data.get('competitors', {}).get('data', [])),
            "job_listings_count": len(all_data.get('job_listings', {}).get('data', []))
        }
        
        parser = PydanticOutputParser(pydantic_object=CompanyAnalysis)
        
        prompt = PromptTemplate(
            template="""As a recruiting analyst, provide final analysis for {company_name}:

Data Summary: {data_summary}

{format_instructions}

Focus on: recruitment viability, company stability, cultural fit, growth potential.""",
            input_variables=["company_name", "data_summary"],
            partial_variables={"format_instructions": parser.get_format_instructions()}
        )
        
        with get_openai_callback() as cb:
            response = self.llm_premium.invoke(prompt.format(
                company_name=company_name,
                data_summary=json.dumps(condensed_data, indent=2)
            ))
            self.total_tokens += cb.total_tokens
        
        try:
            content = response.content
            if not isinstance(content, str):
                content = str(content)
            return parser.parse(content)
        except:
            return CompanyAnalysis(
                executive_summary=f"Analysis completed for {company_name} with mixed data quality.",
                key_insights=["Data collection completed", "Mixed confidence levels", "Requires manual review"],
                missing_data_assessment="Several data points missing or incomplete",
                confidence_rationale="Limited by data source availability"
            )

    def create_optimized_report(self, company_name: str, email: str, research_data: Dict, analysis: CompanyAnalysis) -> str:
        """Create report without additional LLM calls"""
        clean_name = self.clean_company_name(company_name)
        filename = f"{clean_name}_report.md"
        print(f"[DEBUG] Writing report to {filename}")
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"# {company_name} Company Analysis\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Contact Email:** {email}\n")
            f.write(f"**Total Tokens Used:** {self.total_tokens}\n\n")
            print("[DEBUG] Wrote header and meta info")
            
            # Executive Summary
            f.write("## Executive Summary\n\n")
            f.write(f"{analysis.executive_summary}\n\n")
            print("[DEBUG] Wrote executive summary")
            
            # Key Insights
            f.write("## Key Insights for Recruiters\n\n")
            for insight in analysis.key_insights:
                f.write(f"- {insight}\n")
            f.write("\n")
            print("[DEBUG] Wrote key insights")
            
            # Company Overview
            overview = research_data.get('overview', {})
            f.write(f"## Company Overview\n")
            f.write(f"**Confidence Score:** {overview.get('confidence', 0)}\n\n")
            
            overview_data = overview.get('data', {})
            financials = research_data.get('financials', {}).get('data', {})
            f.write(f"- **Name:** {company_name}\n")
            f.write(f"- **Description:** {overview_data.get('description', 'Not available')}\n")
            f.write(f"- **Founded:** {overview_data.get('founded', 'Not available')}\n")
            
            # Founders (list or string, with fallback to history)
            founders = overview_data.get('founders')
            if not founders:
                # Try to extract from history
                history = overview_data.get('history', [])
                if isinstance(history, list):
                    for event in history:
                        event_text = str(event.get('event', ''))
                        if 'founded by' in event_text.lower():
                            # Try to extract founders from the event text
                            after_by = event_text.lower().split('founded by', 1)[-1].strip()
                            # Remove year or extra text
                            after_by = after_by.split(' in ')[0].split(',')[0].strip()
                            founders = [after_by.title()]
                            break
            if isinstance(founders, list):
                f.write(f"- **Founders:** {', '.join(founders)}\n")
            elif founders:
                f.write(f"- **Founders:** {founders}\n")
            else:
                f.write(f"- **Founders:** Not available\n")

            # Headquarters (with fallback to history)
            headquarters = overview_data.get('headquarters')
            if not headquarters:
                history = overview_data.get('history', [])
                if isinstance(history, list):
                    for event in history:
                        event_text = str(event.get('event', ''))
                        for kw in ['headquarters', 'based in', 'located in']:
                            if kw in event_text.lower():
                                # Extract location after keyword
                                after_kw = event_text.lower().split(kw, 1)[-1].strip()
                                after_kw = after_kw.split('.')[0].split(',')[0].strip()
                                headquarters = after_kw.title()
                                break
                        if headquarters:
                            break
            f.write(f"- **Headquarters:** {headquarters if headquarters else 'Not available'}\n")

            f.write(f"- **Ownership:** {overview_data.get('ownership', 'Not available')}\n")

            # Employee count (with fallback to financials)
            employee_count = overview_data.get('employee_count')
            if not employee_count:
                employee_count = financials.get('employee_count')
            if employee_count:
                try:
                    employee_count_str = f"{int(employee_count):,}"
                except Exception:
                    employee_count_str = str(employee_count)
                f.write(f"- **Employee Count:** {employee_count_str}\n")
            else:
                f.write(f"- **Employee Count:** Not available\n")

            # Office Locations
            office_locations = overview_data.get('office_locations', [])
            if office_locations:
                f.write(f"- **Office Locations:** {', '.join(office_locations)}\n")
            else:
                f.write(f"- **Office Locations:** Not available\n")

            # History (as a bulleted list)
            history = overview_data.get('history', [])
            if history:
                f.write(f"\n**History:**\n")
                for event in history:
                    year = event.get('year', '')
                    event_text = event.get('event', '')
                    if year and event_text:
                        f.write(f"- {year}: {event_text}\n")
                    elif event_text:
                        f.write(f"- {event_text}\n")
            f.write("\n")
            print("[DEBUG] Wrote company overview")
            
            # Financial Snapshot
            financials = research_data.get('financials', {})
            f.write(f"## Financial Snapshot\n")
            f.write(f"**Confidence Score:** {financials.get('confidence', 0)}\n\n")
            
            financial_data = financials.get('data', {}).get('financial_data', {})
            if financial_data:
                f.write(f"- **Company Name:** {financial_data.get('company_name', 'N/A')}\n")
                f.write(f"- **Ticker:** {financial_data.get('ticker', 'N/A')}\n")
                f.write(f"- **Exchange:** {financial_data.get('exchange', 'N/A')}\n")
                f.write(f"- **Currency:** {financial_data.get('currency', 'N/A')}\n")
                f.write(f"- **Market Cap:** {financial_data.get('market_cap', 'N/A')}\n")
                f.write(f"- **Enterprise Value:** {financial_data.get('enterprise_value', 'N/A')}\n")
                f.write(f"- **Revenue (TTM):** {financial_data.get('revenue_ttm', 'N/A')}\n")
                f.write(f"- **Revenue Growth:** {financial_data.get('revenue_growth', 'N/A')}\n")
                f.write(f"- **Net Income:** {financial_data.get('net_income', 'N/A')}\n")
                f.write(f"- **PE Ratio:** {financial_data.get('pe_ratio', 'N/A')}\n")
                f.write(f"- **Current Ratio:** {financial_data.get('current_ratio', 'N/A')}\n")
                f.write(f"- **ROE:** {financial_data.get('roe', 'N/A')}\n")
                f.write(f"- **Employees:** {financial_data.get('employees', 'N/A')}\n")
                f.write(f"- **Sector:** {financial_data.get('sector', 'N/A')}\n")
                f.write(f"- **Industry:** {financial_data.get('industry', 'N/A')}\n\n")
            print("[DEBUG] Wrote financial snapshot")
            
            # News Analysis
            news_analysis = research_data.get('news_analysis') or {}
            news_data = research_data.get('news', {}).get('data', {}).get('news_research', {})
            print(f"[DEBUG] News data for report: {news_data}")
            if news_analysis or news_data:
                f.write(f"## Recent News & Sentiment Analysis\n")
                # Sentiment Score fallback
                sentiment_score = news_analysis.get('sentiment_score', None)
                if (sentiment_score is None or sentiment_score == 0.0) and news_data.get('sentiment_summary'):
                    ss = news_data['sentiment_summary']
                    pos = ss.get('positive', 0)
                    neg = ss.get('negative', 0)
                    total = ss.get('total', 0)
                    if total > 0:
                        sentiment_score = round((pos - neg) / total, 2)
                if sentiment_score is not None:
                    f.write(f"**Sentiment Score:** {sentiment_score}\n")
                else:
                    f.write(f"**Sentiment Score:** N/A\n")
                # Controversy Level fallback
                controversy_level = news_analysis.get('controversy_level', None)
                if (not controversy_level or controversy_level == 'LOW') and news_data.get('controversies'):
                    if len(news_data['controversies']) > 3:
                        controversy_level = 'HIGH'
                    elif len(news_data['controversies']) > 0:
                        controversy_level = 'MEDIUM'
                    else:
                        controversy_level = 'LOW'
                if controversy_level:
                    f.write(f"**Controversy Level:** {controversy_level}\n\n")
                else:
                    f.write(f"**Controversy Level:** N/A\n\n")
                    f.write("### Key Themes\n")
                    for theme in news_analysis.get('key_themes', []):
                        f.write(f"- {theme}\n")
                    f.write("\n")
                    f.write("### Recruiter Concerns\n")
                    for concern in news_analysis.get('recruiter_concerns', []):
                        f.write(f"- {concern}\n")
                    f.write("\n")
                # Add positive, negative, future plans, controversies from news_data
                if news_data.get('positive_examples'):
                    f.write("### Recent Positive News\n")
                    for item in news_data['positive_examples']:
                        f.write(f"- {item.get('title', '')}\n")
                    f.write("\n")
                if news_data.get('negative_examples'):
                    f.write("### Recent Negative News\n")
                    for item in news_data['negative_examples']:
                        f.write(f"- {item.get('title', '')}\n")
                    f.write("\n")
                if news_data.get('future_plans'):
                    f.write("### Future Plans / Announcements\n")
                    for item in news_data['future_plans']:
                        f.write(f"- {item.get('title', '')}\n")
                    f.write("\n")
                if news_data.get('controversies'):
                    f.write("### Recent Controversies\n")
                    for item in news_data['controversies']:
                        f.write(f"- {item.get('title', '')}\n")
                    f.write("\n")
            print("[DEBUG] Wrote news analysis")
            
            # Social Media
            social_media = research_data.get('social_media', {})
            f.write(f"## Social Media Research\n")
            f.write(f"**Confidence Score:** {social_media.get('confidence', 0)}\n\n")
            
            social_data = social_media.get('data', {})
            if social_data.get('linkedin'):
                linkedin = social_data['linkedin']
                f.write(f"- **LinkedIn**\n")
                f.write(f"  - URL: [{linkedin.get('url', 'N/A')}]({linkedin.get('url', '#')})\n")
                f.write(f"  - Followers: {linkedin.get('followers', 'N/A')}\n")
                f.write(f"  - Employees: {linkedin.get('employees', 'N/A')}\n")
            
            if social_data.get('youtube'):
                youtube = social_data['youtube']
                f.write(f"- **YouTube**\n")
                f.write(f"  - URL: [{youtube.get('url', 'N/A')}]({youtube.get('url', '#')})\n")
                f.write(f"  - Subscribers: {youtube.get('subscribers', 'N/A')}\n")
            f.write("\n")
            
            # Competitors
            competitors = research_data.get('competitors', {})
            import json
            print("[DEBUG] Competitor data for report:", json.dumps(competitors, indent=2))
            f.write(f"## Direct Competitors\n")
            f.write(f"**Confidence Score:** {competitors.get('confidence', 0)}\n\n")
            
            def human_readable_number(n):
                if n is None:
                    return 'N/A'
                if n >= 1_000_000_000:
                    return f"{n/1_000_000_000:.1f}B"
                elif n >= 1_000_000:
                    return f"{n/1_000_000:.1f}M"
                elif n >= 1_000:
                    return f"{n/1_000:.1f}K"
                return str(n)

            for competitor in competitors.get('data', []):
                if isinstance(competitor, dict):
                    f.write(f"- **{competitor.get('name', 'Unknown')}**\n")
                    f.write(f"  - Domain: {competitor.get('domain', 'N/A')}\n")
                    # Employees
                    emp_min = competitor.get('employees_min')
                    emp_max = competitor.get('employees_max')
                    if emp_min and emp_max:
                        f.write(f"  - Employees: {human_readable_number(emp_min)}–{human_readable_number(emp_max)}\n")
                    elif emp_min:
                        f.write(f"  - Employees: {human_readable_number(emp_min)}\n")
                    else:
                        f.write(f"  - Employees: N/A\n")
                    # Revenue
                    rev_min = competitor.get('revenue_min')
                    rev_max = competitor.get('revenue_max')
                    if rev_min and rev_max:
                        f.write(f"  - Revenue: ${human_readable_number(rev_min)}–${human_readable_number(rev_max)}\n")
                    elif rev_min:
                        f.write(f"  - Revenue: ${human_readable_number(rev_min)}\n")
                    else:
                        f.write(f"  - Revenue: N/A\n")
                    # Visits
                    visits = competitor.get('total_visits')
                    f.write(f"  - Visits: {human_readable_number(visits)}\n")
                    # HQ
                    hq_city = competitor.get('hq_city')
                    hq_country = competitor.get('hq_country')
                    if hq_city and hq_country:
                        f.write(f"  - HQ: {hq_city}, {hq_country}\n")
                    elif hq_city:
                        f.write(f"  - HQ: {hq_city}\n")
                    elif hq_country:
                        f.write(f"  - HQ: {hq_country}\n")
                    else:
                        f.write(f"  - HQ: N/A\n")
                    # Icon
                    if competitor.get('icon'):
                        f.write(f"  - ![icon]({competitor['icon']})\n")
            f.write("\n")
            
            # Glassdoor Analysis
            glassdoor_analysis = research_data.get('glassdoor_analysis')
            if glassdoor_analysis:
                f.write(f"## Glassdoor Analysis\n")
                f.write(f"**Overall Sentiment:** {glassdoor_analysis.get('overall_sentiment')}\n\n")
                
                f.write("### Top Pros\n")
                for pro in glassdoor_analysis.get('top_pros', []):
                    f.write(f"- {pro}\n")
                f.write("\n")
                
                f.write("### Top Cons\n")
                for con in glassdoor_analysis.get('top_cons', []):
                    f.write(f"- {con}\n")
                f.write("\n")
                
                f.write("### Recruiter Notes\n")
                for note in glassdoor_analysis.get('recruiter_notes', []):
                    f.write(f"- {note}\n")
                f.write("\n")
            
            # Job Listings
            job_listings = research_data.get('job_listings', {})
            f.write(f"## Active Job Ads\n")
            f.write(f"**Confidence Score:** {job_listings.get('confidence', 0)}\n\n")
            
            for job in job_listings.get('data', [])[:4]:  # Show top 4
                if isinstance(job, dict):
                    f.write(f"- **{job.get('title', 'Unknown Position')}**\n")
                    f.write(f"  - Location: {job.get('location', 'N/A')}\n")
                    f.write(f"  - Company: {job.get('company', 'N/A')}\n")
                    f.write(f"  - Type: {job.get('job_type', 'N/A')}\n")
                    if job.get('url'):
                        f.write(f"  - URL: [{job.get('url')}]({job.get('url')})\n")
            f.write("\n")
            
            # Analysis Summary
            f.write("## Analysis Summary\n\n")
            f.write(f"**Missing Data Assessment:** {analysis.missing_data_assessment}\n\n")
            f.write(f"**Confidence Rationale:** {analysis.confidence_rationale}\n\n")
            
            f.write("---\n")
            f.write(f"*Report generated with {self.total_tokens} tokens*\n")
        
        return filename

    def run_token_optimized_research(self, company_name: str, email: str):
        """Run research with minimal token usage"""
        print(f"Starting token-optimized research for: {company_name}")
        print(f"Using GPT-4o-mini for analysis, GPT-4o for final synthesis")
        
        # Collect all data first (no LLM calls)
        print("Collecting raw data...")
        
        overview = get_best_overview(company_name)
        financials = FinancialSnapshot().research_company_financials(company_name)
        
        # --- NEWS TOOL FULL PIPELINE ---
        news_data = research_company_news(company_name)
        if news_data:
            sentiment = analyze_news_sentiment(news_data)
            controversies = detect_controversies(news_data)
            future_plans = extract_future_plans(news_data)
            news_structured = structure_research_data(company_name, email, news_data, sentiment, controversies, future_plans)
        else:
            news_structured = {}
        
        social_media = SocialMediaResearcher(company_name).research_all_platforms()
        
        company_domain = company_name.lower().replace(" ", "").replace(".", "") + ".com"
        competitors = get_competitor_summary(company_domain)
        
        customers = ClientResearchTool().research_company_clients(company_name)
        glassdoor_raw = get_glassdoor_summary(company_name)
        job_listings = get_job_listings(company_name)
        
        # Calculate confidence scores (no LLM calls)
        research_data = {
            "overview": {
                "confidence": self.calculate_confidence_score(json.dumps(overview)),
                "data": overview  # full dict
            },
            "financials": {
                "confidence": self.calculate_confidence_score(json.dumps(financials)),
                "data": financials  # full dict
            },
            "social_media": {
                "confidence": self.calculate_confidence_score(json.dumps(social_media)),
                "data": social_media  # full dict
            },
            "competitors": {
                "confidence": self.calculate_confidence_score(json.dumps(competitors)),
                "data": competitors.get('competitors', [])  # full list of dicts
            },
            "customers": {
                "confidence": self.calculate_confidence_score(json.dumps(dataclass_to_dict(getattr(customers, 'major_clients', [])))),
                "data": summarize_list(list(dataclass_to_dict(getattr(customers, 'major_clients', []))))
            },
            "job_listings": {
                "confidence": self.calculate_confidence_score(json.dumps(job_listings)),
                "data": job_listings  # full list/dict
            },
            "news": {
                "confidence": self.calculate_confidence_score(json.dumps(news_structured)),
                "data": news_structured  # structured dict with all fields
            }
        }
        
        # Make strategic LLM calls (only 3 total)
        print("Making strategic LLM calls...")
        
        # 1. Analyze news (mini model)
        news_analysis = self.analyze_news_efficiently(news_data or {}) # Use news_data directly here
        research_data["news_analysis"] = news_analysis.model_dump()
        
        # 2. Analyze Glassdoor (mini model)
        glassdoor_analysis = self.analyze_glassdoor_efficiently(glassdoor_raw.get('reviews', []))
        research_data["glassdoor_analysis"] = glassdoor_analysis.model_dump()
        
        # 3. Final comprehensive analysis (premium model)
        final_analysis = self.generate_final_analysis(company_name, research_data)
        
        # Debug print of research_data before report generation
        print("\n===== DEBUG: research_data before report generation =====")
        pprint.pprint(research_data)
        print("===== END DEBUG =====\n")
        
        # Generate report (no LLM calls)
        print("Generating report...")
        filename = self.create_optimized_report(company_name, email, research_data, final_analysis)
        
        # Generate JSON
        json_filename = f"{self.clean_company_name(company_name)}_data.json"
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump({
                "research_data": research_data,
                "final_analysis": final_analysis.model_dump(),
                "token_usage": self.total_tokens
            }, f, indent=2, ensure_ascii=False, default=str)
        
        return filename, json_filename

def get_best_overview(company_name):
    # Generate candidate names
    candidates = [
        company_name,
        company_name.capitalize(),
        company_name.title(),
        company_name + ", Inc.",
        company_name.capitalize() + ", Inc.",
        company_name.title() + ", Inc.",
        company_name + " Inc.",
        company_name.capitalize() + " Inc.",
        company_name.title() + " Inc.",
    ]
    # Special case for Google
    if company_name.lower() == "google":
        candidates.append("Alphabet Inc.")
    # Remove duplicates and empty
    candidates = [c for i, c in enumerate(candidates) if c and c not in candidates[:i]]
    # Try direct matches
    for name in candidates:
        overview = research_company_overview(name)
        if overview.get("founded") or overview.get("history") or overview.get("founders"):
            print(f"[DEBUG] Overview found for: {name}")
            return overview
    # Fuzzy match using Wikipedia search
    try:
        search_results = wikipedia.search(company_name)
        close_matches = difflib.get_close_matches(company_name, search_results, n=3, cutoff=0.6)
        for match in close_matches:
            overview = research_company_overview(match)
            if overview.get("founded") or overview.get("history") or overview.get("founders"):
                print(f"[DEBUG] Overview found for fuzzy match: {match}")
                return overview
    except Exception as e:
        print(f"[DEBUG] Wikipedia fuzzy search error: {e}")
    print("[DEBUG] No detailed overview found, using last attempt.")
    return research_company_overview(company_name)  # Return last attempt even if empty

def main():
    load_dotenv()
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY not found in environment. Please set it in your .env file.")

    parser = argparse.ArgumentParser(description="Token-Optimized Company Research Agent")
    parser.add_argument("--company", required=True, help="Company name to research")
    parser.add_argument("--email", required=True, help="Contact email address")
    args = parser.parse_args()

    # Initialize token-optimized researcher
    researcher = TokenOptimizedResearcher(openai_api_key)
    
    # Run research
    try:
        start_time = datetime.now()
        md_file, json_file = researcher.run_token_optimized_research(args.company, args.email)
        end_time = datetime.now()
        
        print(f"\n=== Research Complete ===")
        print(f"Duration: {end_time - start_time}")
        print(f"Total Tokens Used: {researcher.total_tokens}")
        print(f"Estimated Cost: ${researcher.total_tokens * 0.00015:.4f}")  # Rough estimate
        print(f"Report: {os.path.abspath(md_file)}")
        print(f"Data: {os.path.abspath(json_file)}")
        
    except Exception as e:
        print(f"Error during research: {str(e)}")
        raise

if __name__ == "__main__":
    main()