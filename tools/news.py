import argparse
from newsapi import NewsApiClient
import os
from datetime import datetime, timedelta
import urllib3

# Suppress SSL warning
urllib3.disable_warnings(urllib3.exceptions.NotOpenSSLWarning)

def get_inputs():
    parser = argparse.ArgumentParser(description="Research Agent CLI")
    parser.add_argument("--company", required=True, help="Company name")
    parser.add_argument("--email", required=True, help="Contact email")
    args = parser.parse_args()
    return args.company, args.email

def research_company_news(company_name):
    """Research company using News API"""
    # Initialize the News API client
    # Replace with your actual API key or use environment variable
    api_key = '5ceffb7fc5f5418492791c720d0a860b'  # Your API key
    newsapi = NewsApiClient(api_key=api_key)
    
    print(f"🔍 Researching news for: {company_name}")
    
    try:
        # Get recent news (last 30 days)
        from_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        to_date = datetime.now().strftime('%Y-%m-%d')
        
        # Search for company news
        all_articles = newsapi.get_everything(
            q=company_name,
            from_param=from_date,
            to=to_date,
            language='en',
            sort_by='relevancy',
            page_size=20  # Limit to 20 articles
        )
        
        print(f"📰 Found {all_articles['totalResults']} articles")
        print("=" * 60)
        
        # Process and display articles
        for i, article in enumerate(all_articles['articles'][:5], 1):  # Show top 5
            print(f"\n{i}. {article['title']}")
            print(f"   Source: {article['source']['name']}")
            print(f"   Published: {article['publishedAt']}")
            print(f"   URL: {article['url']}")
            if article['description']:
                print(f"   Description: {article['description'][:200]}...")
        
        return all_articles
        
    except Exception as e:
        print(f"❌ Error fetching news: {str(e)}")
        return None

def analyze_news_sentiment(articles):
    """Enhanced analysis of news articles"""
    if not articles or not articles['articles']:
        return "No articles to analyze"
    
    total_articles = len(articles['articles'])
    
    # Expanded keyword lists
    negative_keywords = [
        'controversy', 'lawsuit', 'scandal', 'decline', 'loss', 'fired', 'problem',
        'drop', 'decrease', 'fall', 'worst', 'crash', 'fails', 'wrong', 'mistake',
        'regulatory', 'vacuum', 'caught', 'fucked', 'fucking', 'low', 'down',
        'challenge', 'issue', 'concern', 'warning', 'risk', 'threat', 'crisis'
    ]
    positive_keywords = [
        'growth', 'success', 'expansion', 'funding', 'award', 'innovation', 'profit',
        'launch', 'first', 'breakthrough', 'achievement', 'delivered', 'autonomous',
        'robotaxi', 'service', 'completed', 'strong', 'record', 'best', 'win',
        'milestone', 'advance', 'progress', 'improve', 'boost', 'rise', 'up'
    ]
    
    articles_analysis = []
    negative_count = 0
    positive_count = 0
    
    for article in articles['articles']:
        title_lower = article['title'].lower()
        desc_lower = (article['description'] or '').lower()
        
        sentiment = 'neutral'
        matched_keywords = []
        
        # Check for negative sentiment
        for keyword in negative_keywords:
            if keyword in title_lower or keyword in desc_lower:
                negative_count += 1
                sentiment = 'negative'
                matched_keywords.append(keyword)
                break
        
        # Check for positive sentiment (only if not already negative)
        if sentiment == 'neutral':
            for keyword in positive_keywords:
                if keyword in title_lower or keyword in desc_lower:
                    positive_count += 1
                    sentiment = 'positive'
                    matched_keywords.append(keyword)
                    break
        
        articles_analysis.append({
            'title': article['title'],
            'sentiment': sentiment,
            'url': article['url'],
            'source': article['source']['name'],
            'published': article['publishedAt'],
            'keywords': matched_keywords
        })
    
    print(f"\n📊 News Sentiment Analysis:")
    print(f"   Total articles: {total_articles}")
    print(f"   Potentially positive: {positive_count}")
    print(f"   Potentially negative: {negative_count}")
    print(f"   Neutral/Mixed: {total_articles - positive_count - negative_count}")
    
    # Show some examples
    positive_examples = [a for a in articles_analysis if a['sentiment'] == 'positive'][:3]
    negative_examples = [a for a in articles_analysis if a['sentiment'] == 'negative'][:3]
    
    if positive_examples:
        print(f"\n📈 Positive Examples:")
        for article in positive_examples:
            print(f"   • {article['title']}")
            print(f"     Keywords: {', '.join(article['keywords'])}")
    
    if negative_examples:
        print(f"\n📉 Negative Examples:")
        for article in negative_examples:
            print(f"   • {article['title']}")
            print(f"     Keywords: {', '.join(article['keywords'])}")
    
    return {
        'total': total_articles,
        'positive': positive_count,
        'negative': negative_count,
        'neutral': total_articles - positive_count - negative_count,
        'articles': articles_analysis,
        'positive_examples': positive_examples,
        'negative_examples': negative_examples
    }

def detect_controversies(articles):
    """Detect controversies in news articles"""
    if not articles or not articles['articles']:
        return []
    
    controversy_keywords = ['lawsuit', 'scandal', 'investigation', 'fine', 'penalty', 'controversy', 'criticized', 'accused']
    
    controversies = []
    for article in articles['articles']:
        title_lower = article['title'].lower()
        desc_lower = (article['description'] or '').lower()
        matched_keywords = [kw for kw in controversy_keywords if kw in title_lower or kw in desc_lower]
        if matched_keywords:
            controversies.append({
                'title': article['title'],
                'url': article['url'],
                'source': article['source']['name'],
                'published': article['publishedAt'],
                'keywords': matched_keywords
            })
    
    print(f"\n⚠️ Detected {len(controversies)} potential controversies")
    for i, item in enumerate(controversies[:3], 1):
        print(f"   {i}. {item['title']}")
        print(f"      Keywords: {', '.join(item['keywords'])}")
    
    return controversies

def extract_future_plans(articles):
    """Extract future plans from news articles"""
    if not articles or not articles['articles']:
        return []
    
    future_keywords = ['expansion', 'hiring', 'plans to', 'will launch', 'upcoming', 'announced']
    
    future_plans = []
    for article in articles['articles']:
        title_lower = article['title'].lower()
        desc_lower = (article['description'] or '').lower()
        matched_keywords = [kw for kw in future_keywords if kw in title_lower or kw in desc_lower]
        if matched_keywords:
            future_plans.append({
                'title': article['title'],
                'url': article['url'],
                'source': article['source']['name'],
                'published': article['publishedAt'],
                'keywords': matched_keywords
            })
    
    print(f"\n🔮 Detected {len(future_plans)} future plans/announcements")
    for i, item in enumerate(future_plans[:3], 1):
        print(f"   {i}. {item['title']}")
        print(f"      Keywords: {', '.join(item['keywords'])}")
    
    return future_plans

def structure_research_data(company_name, email, news_data, sentiment_analysis, controversies, future_plans):
    """Structure the research data for report generation"""
    return {
        'company_name': company_name,
        'contact_email': email,
        'research_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'news_research': {
            'total_articles_found': news_data['totalResults'],
            'articles_analyzed': len(news_data['articles']),
            'sentiment_summary': {
                'positive': sentiment_analysis['positive'],
                'negative': sentiment_analysis['negative'],
                'neutral': sentiment_analysis['neutral'],
                'total': sentiment_analysis['total']
            },
            'key_articles': news_data['articles'][:5],  # Top 5 articles
            'positive_examples': sentiment_analysis['positive_examples'],
            'negative_examples': sentiment_analysis['negative_examples'],
            'controversies': controversies[:5],  # Top 5 controversies
            'future_plans': future_plans[:5],  # Top 5 future plans
            'confidence_score': calculate_confidence_score(news_data, sentiment_analysis)
        }
    }

def calculate_confidence_score(news_data, sentiment_analysis):
    """Calculate confidence score based on data quality"""
    score = 0.0
    
    # Base score from number of articles
    total_articles = news_data['totalResults']
    if total_articles > 100:
        score += 0.4
    elif total_articles > 50:
        score += 0.3
    elif total_articles > 10:
        score += 0.2
    else:
        score += 0.1
    
    # Score from article recency (articles analyzed are from last 30 days)
    score += 0.3
    
    # Score from sentiment analysis coverage
    analyzed_articles = sentiment_analysis['total']
    if analyzed_articles >= 20:
        score += 0.2
    elif analyzed_articles >= 10:
        score += 0.15
    else:
        score += 0.1
    
    # Score from data diversity (having both positive and negative articles)
    if sentiment_analysis['positive'] > 0 and sentiment_analysis['negative'] > 0:
        score += 0.1
    elif sentiment_analysis['positive'] > 0 or sentiment_analysis['negative'] > 0:
        score += 0.05
    
    return min(score, 1.0)  # Cap at 1.0

def display_research_summary(research_data):
    """Display a summary of research findings"""
    news = research_data['news_research']
    
    print(f"\n" + "=" * 60)
    print(f"📋 RESEARCH SUMMARY FOR {research_data['company_name'].upper()}")
    print(f"=" * 60)
    print(f"📅 Research Date: {research_data['research_date']}")
    print(f"📧 Contact Email: {research_data['contact_email']}")
    print(f"🎯 Confidence Score: {news['confidence_score']:.2f}/1.00")
    
    print(f"\n📰 NEWS ANALYSIS:")
    print(f"   • Total articles found: {news['total_articles_found']:,}")
    print(f"   • Articles analyzed: {news['articles_analyzed']}")
    print(f"   • Positive sentiment: {news['sentiment_summary']['positive']}")
    print(f"   • Negative sentiment: {news['sentiment_summary']['negative']}")
    print(f"   • Neutral sentiment: {news['sentiment_summary']['neutral']}")
    
    if news['positive_examples']:
        print(f"\n🟢 Recent Positive News:")
        for article in news['positive_examples']:
            print(f"   • {article['title']}")
    
    if news['negative_examples']:
        print(f"\n🔴 Recent Negative News:")
        for article in news['negative_examples']:
            print(f"   • {article['title']}")
    
    if news.get('controversies'):
        print(f"\n⚠️ Recent Controversies:")
        for item in news['controversies']:
            print(f"   • {item['title']}")
    
    if news.get('future_plans'):
        print(f"\n🔮 Future Plans/Announcements:")
        for item in news['future_plans']:
            print(f"   • {item['title']}")

if __name__ == "__main__":
    company, email = get_inputs()
    print(f"🏢 Company: {company}")
    print(f"📧 Email: {email}")
    print("\n" + "=" * 60)
    
    # Research company news
    news_data = research_company_news(company)
    
    if news_data:
        # Analyze the sentiment
        sentiment = analyze_news_sentiment(news_data)
        
        # Detect controversies and future plans
        controversies = detect_controversies(news_data)
        future_plans = extract_future_plans(news_data)
        
        # Structure the data
        research_results = structure_research_data(company, email, news_data, sentiment, controversies, future_plans)
        
        # Display summary
        display_research_summary(research_results)
        
        print(f"\n✅ Research completed for {company}")
        
        # Optional: Save to file
        import json
        filename = f"{company.replace(' ', '_').lower()}_research.json"
        with open(filename, 'w') as f:
            json.dump(research_results, f, indent=2, default=str)
        print(f"💾 Research data saved to: {filename}")
        
    else:
        print(f"\n❌ Could not complete research for {company}")