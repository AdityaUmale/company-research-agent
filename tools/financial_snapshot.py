
import yfinance as yf
import requests
import re
from datetime import datetime, timedelta
import json
import time
from typing import Dict, Optional, List, Any

class FinancialSnapshot:
    def __init__(self, alpha_vantage_key: Optional[str] = None):
        """
        Initialize Financial Snapshot with optional Alpha Vantage API key
        Get free key from: https://www.alphavantage.co/support/#api-key
        """
        self.alpha_vantage_key = alpha_vantage_key
        self.alpha_vantage_base_url = "https://www.alphavantage.co/query"
        
    def search_company_ticker(self, company_name: str) -> Optional[str]:
        """
        Search for company ticker symbol using multiple methods
        """
        # Method 1: Try Alpha Vantage Symbol Search
        if self.alpha_vantage_key:
            ticker = self._search_ticker_alpha_vantage(company_name)
            if ticker:
                return ticker
        
        # Method 2: Try yfinance direct search with common patterns
        ticker = self._search_ticker_yfinance(company_name)
        if ticker:
            return ticker
        
        # Method 3: Try common ticker patterns
        ticker = self._guess_ticker_patterns(company_name)
        return ticker
    
    def _search_ticker_alpha_vantage(self, company_name: str) -> Optional[str]:
        """Search ticker using Alpha Vantage Symbol Search"""
        try:
            params = {
                'function': 'SYMBOL_SEARCH',
                'keywords': company_name,
                'apikey': self.alpha_vantage_key
            }
            
            response = requests.get(self.alpha_vantage_base_url, params=params, timeout=10)
            data = response.json()
            
            if 'bestMatches' in data and data['bestMatches']:
                # Get the first best match
                best_match = data['bestMatches'][0]
                return best_match.get('1. symbol')
                
        except Exception as e:
            print(f"⚠️  Alpha Vantage search failed: {e}")
            
        return None
    
    def _search_ticker_yfinance(self, company_name: str) -> Optional[str]:
        """Search ticker using yfinance with common patterns"""
        # Common ticker patterns to try
        patterns = [
            company_name.upper(),  # Direct name
            company_name.split()[0].upper(),  # First word
            company_name.replace(' ', '').upper(),  # No spaces
            company_name.replace(',', '').replace('.', '').split()[0].upper(),  # Clean first word
        ]
        
        for pattern in patterns:
            try:
                # Try with common suffixes
                candidates = [pattern, f"{pattern}.TO", f"{pattern}.L", f"{pattern}.F"]
                
                for candidate in candidates:
                    try:
                        ticker = yf.Ticker(candidate)
                        info = ticker.info
                        
                        # Check if it's a valid ticker with company info
                        if info.get('longName') or info.get('shortName'):
                            # Verify it's the right company (basic check)
                            company_names = [
                                info.get('longName', '').lower(),
                                info.get('shortName', '').lower()
                            ]
                            
                            if any(word in name for word in company_name.lower().split()[:2] 
                                  for name in company_names if name):
                                return candidate
                                
                    except Exception:
                        continue
                        
            except Exception:
                continue
                
        return None
    
    def _guess_ticker_patterns(self, company_name: str) -> Optional[str]:
        """Guess ticker based on common patterns"""
        # Clean company name
        clean_name = re.sub(r'[^\w\s]', '', company_name)
        words = clean_name.split()
        
        if not words:
            return None
        
        # Common patterns for well-known companies
        known_patterns = {
            'tesla': 'TSLA',
            'apple': 'AAPL',
            'microsoft': 'MSFT',
            'google': 'GOOGL',
            'alphabet': 'GOOGL',
            'amazon': 'AMZN',
            'facebook': 'META',
            'meta': 'META',
            'netflix': 'NFLX',
            'nvidia': 'NVDA',
            'walmart': 'WMT',
            'disney': 'DIS',
            'boeing': 'BA',
            'coca cola': 'KO',
            'mcdonalds': 'MCD',
            'visa': 'V',
            'mastercard': 'MA',
            'paypal': 'PYPL',
            'uber': 'UBER',
            'airbnb': 'ABNB',
            'zoom': 'ZM',
            'slack': 'WORK',
            'twitter': 'TWTR',  # Historical
            'x corp': 'TWTR',   # Historical
        }
        
        # Check for known patterns
        company_lower = company_name.lower()
        for pattern, ticker in known_patterns.items():
            if pattern in company_lower:
                return ticker
        
        # Try first word + common suffixes
        first_word = words[0].upper()
        candidates = [first_word, f"{first_word}A", f"{first_word}T"]
        
        for candidate in candidates:
            try:
                ticker = yf.Ticker(candidate)
                info = ticker.info
                if info.get('longName'):
                    return candidate
            except Exception:
                continue
                
        return None
    
    def get_public_company_financials(self, ticker: str) -> Dict[str, Any]:
        """Get comprehensive financial data for public companies"""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Get historical data for trends
            hist = stock.history(period="1y")
            
            # Get financial statements
            financials = stock.financials
            balance_sheet = stock.balance_sheet
            cash_flow = stock.cashflow
            
            # Extract key metrics
            financial_data = {
                'company_name': info.get('longName', 'N/A'),
                'ticker': ticker,
                'exchange': info.get('exchange', 'N/A'),
                'currency': info.get('currency', 'USD'),
                'market_cap': info.get('marketCap'),
                'enterprise_value': info.get('enterpriseValue'),
                'revenue_ttm': info.get('totalRevenue'),
                'revenue_growth': info.get('revenueGrowth'),
                'gross_profit': info.get('grossProfits'),
                'operating_income': info.get('operatingCashflow'),
                'net_income': info.get('netIncomeToCommon'),
                'eps': info.get('trailingEps'),
                'pe_ratio': info.get('trailingPE'),
                'price_to_book': info.get('priceToBook'),
                'debt_to_equity': info.get('debtToEquity'),
                'current_ratio': info.get('currentRatio'),
                'roa': info.get('returnOnAssets'),
                'roe': info.get('returnOnEquity'),
                'profit_margin': info.get('profitMargins'),
                'operating_margin': info.get('operatingMargins'),
                'dividend_yield': info.get('dividendYield'),
                'beta': info.get('beta'),
                'fifty_two_week_high': info.get('fiftyTwoWeekHigh'),
                'fifty_two_week_low': info.get('fiftyTwoWeekLow'),
                'current_price': info.get('currentPrice'),
                'target_price': info.get('targetMeanPrice'),
                'recommendation': info.get('recommendationMean'),
                'shares_outstanding': info.get('sharesOutstanding'),
                'float_shares': info.get('floatShares'),
                'employees': info.get('fullTimeEmployees'),
                'sector': info.get('sector'),
                'industry': info.get('industry'),
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Calculate additional metrics
            if financial_data['current_price'] and financial_data['fifty_two_week_low']:
                financial_data['price_change_52w'] = (
                    (financial_data['current_price'] - financial_data['fifty_two_week_low']) / 
                    financial_data['fifty_two_week_low'] * 100
                )
            
            # Format large numbers
            financial_data = self._format_financial_numbers(financial_data)
            
            return {
                'status': 'success',
                'data_type': 'public_company',
                'financial_data': financial_data,
                'confidence_score': 0.9,  # High confidence for public companies
                'sources': [
                    {
                        'type': 'Yahoo Finance',
                        'url': f"https://finance.yahoo.com/quote/{ticker}",
                        'data_points': 'Stock price, financial ratios, company info'
                    }
                ]
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'confidence_score': 0.0
            }
    
    def get_private_company_estimates(self, company_name: str) -> Dict[str, Any]:
        """Get best-effort estimates for private companies"""
        estimates = {
            'company_name': company_name,
            'data_type': 'private_company_estimates',
            'estimated_revenue': None,
            'estimated_valuation': None,
            'funding_info': None,
            'employee_count': None,
            'industry': None,
            'founded_year': None,
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Try to get data from multiple sources
        confidence_score = 0.0
        sources = []
        
        # Method 1: Try to find funding information from news/press releases
        funding_data = self._search_funding_news(company_name)
        if funding_data:
            estimates.update(funding_data)
            confidence_score += 0.3
            sources.append({
                'type': 'News/Press Releases',
                'data_points': 'Funding rounds, valuation estimates'
            })
        
        # Method 2: Industry-based estimates
        industry_estimates = self._get_industry_estimates(company_name)
        if industry_estimates:
            estimates.update(industry_estimates)
            confidence_score += 0.2
            sources.append({
                'type': 'Industry Analysis',
                'data_points': 'Industry benchmarks, size estimates'
            })
        
        # Method 3: Employee-based revenue estimates
        if estimates.get('employee_count'):
            industry = estimates.get('industry') or 'default'
            revenue_estimate = self._estimate_revenue_from_employees(
                estimates['employee_count'],
                industry
            )
            if revenue_estimate:
                estimates['estimated_revenue'] = revenue_estimate
                confidence_score += 0.1
        
        return {
            'status': 'success',
            'data_type': 'private_company',
            'financial_data': estimates,
            'confidence_score': min(confidence_score, 0.6),  # Cap at 0.6 for estimates
            'sources': sources
        }
    
    def _search_funding_news(self, company_name: str) -> Optional[Dict]:
        """Search for recent funding news (simplified implementation)"""
        # This is a simplified version - in production, you'd use news APIs
        # or web scraping to find recent funding announcements
        
        # For demo purposes, return None
        # In real implementation, you would:
        # 1. Search news APIs for funding announcements
        # 2. Parse funding amounts and valuations
        # 3. Extract investor information
        return None
    
    def _get_industry_estimates(self, company_name: str) -> Optional[Dict]:
        """Get industry-based estimates (simplified)"""
        # This would typically involve:
        # 1. Determining company industry
        # 2. Looking up industry benchmarks
        # 3. Applying size-based multipliers
        
        # For demo purposes, return basic structure
        return {
            'industry': 'Technology',  # Would be determined programmatically
            'estimated_revenue_multiple': '5-10x employee count (in thousands)'
        }
    
    def _estimate_revenue_from_employees(self, employee_count: int, industry: str) -> Optional[str]:
        """Estimate revenue based on employee count and industry"""
        if not employee_count:
            return None
        
        # Industry-based revenue per employee (rough estimates)
        revenue_per_employee = {
            'technology': 200000,  # $200k per employee
            'software': 250000,    # $250k per employee
            'finance': 300000,     # $300k per employee
            'consulting': 150000,  # $150k per employee
            'manufacturing': 400000, # $400k per employee
            'retail': 100000,      # $100k per employee
            'default': 200000      # Default estimate
        }
        
        multiplier = revenue_per_employee.get(
            industry.lower() if industry else 'default',
            revenue_per_employee['default']
        )
        
        estimated_revenue = employee_count * multiplier
        return self._format_currency(estimated_revenue)
    
    def _format_financial_numbers(self, data: Dict) -> Dict:
        """Format financial numbers for better readability"""
        financial_fields = [
            'market_cap', 'enterprise_value', 'revenue_ttm', 'gross_profit',
            'operating_income', 'net_income', 'current_price', 'target_price',
            'fifty_two_week_high', 'fifty_two_week_low', 'shares_outstanding',
            'float_shares'
        ]
        
        for field in financial_fields:
            if data.get(field) is not None:
                data[f"{field}_formatted"] = self._format_currency(data[field])
        
        return data
    
    def _format_currency(self, amount: float) -> str:
        """Format currency amounts with appropriate suffixes"""
        if amount is None:
            return "N/A"
        
        if amount >= 1e12:
            return f"${amount/1e12:.2f}T"
        elif amount >= 1e9:
            return f"${amount/1e9:.2f}B"
        elif amount >= 1e6:
            return f"${amount/1e6:.2f}M"
        elif amount >= 1e3:
            return f"${amount/1e3:.2f}K"
        else:
            return f"${amount:.2f}"
    
    def research_company_financials(self, company_name: str) -> Dict[str, Any]:
        """
        Main method to research company financials
        """
        print(f"🔍 Researching financial data for: {company_name}")
        
        # Step 1: Try to find ticker symbol
        ticker = self.search_company_ticker(company_name)
        
        if ticker:
            print(f"📊 Found ticker: {ticker}")
            # Step 2: Get public company data
            result = self.get_public_company_financials(ticker)
            
            if result['status'] == 'success':
                print(f"✅ Successfully retrieved public company data")
                return result
            else:
                print(f"⚠️  Failed to get public data: {result.get('error')}")
        else:
            print(f"📋 No ticker found - treating as private company")
        
        # Step 3: Fallback to private company estimates
        print(f"🔮 Generating private company estimates")
        result = self.get_private_company_estimates(company_name)
        
        return result

def display_financial_snapshot(financial_data: Dict[str, Any]):
    """Display financial snapshot in a formatted way"""
    print(f"\n{'='*60}")
    print(f"💰 FINANCIAL SNAPSHOT")
    print(f"{'='*60}")
    
    if financial_data['status'] == 'error':
        print(f"❌ Error: {financial_data['error']}")
        return
    
    data = financial_data['financial_data']
    data_type = financial_data['data_type']
    
    print(f"🏢 Company: {data['company_name']}")
    print(f"📊 Data Type: {data_type.replace('_', ' ').title()}")
    print(f"🎯 Confidence Score: {financial_data['confidence_score']:.2f}/1.00")
    
    if data_type == 'public_company':
        print(f"\n📈 STOCK INFORMATION:")
        print(f"   • Ticker: {data.get('ticker', 'N/A')}")
        print(f"   • Exchange: {data.get('exchange', 'N/A')}")
        print(f"   • Current Price: {data.get('current_price_formatted', 'N/A')}")
        print(f"   • Market Cap: {data.get('market_cap_formatted', 'N/A')}")
        print(f"   • 52W High/Low: {data.get('fifty_two_week_high_formatted', 'N/A')} / {data.get('fifty_two_week_low_formatted', 'N/A')}")
        
        print(f"\n💵 FINANCIAL METRICS:")
        print(f"   • Revenue (TTM): {data.get('revenue_ttm_formatted', 'N/A')}")
        print(f"   • Net Income: {data.get('net_income_formatted', 'N/A')}")
        print(f"   • Gross Profit: {data.get('gross_profit_formatted', 'N/A')}")
        print(f"   • EPS: {data.get('eps', 'N/A')}")
        
        print(f"\n📊 KEY RATIOS:")
        print(f"   • P/E Ratio: {data.get('pe_ratio', 'N/A')}")
        print(f"   • Price to Book: {data.get('price_to_book', 'N/A')}")
        print(f"   • Debt to Equity: {data.get('debt_to_equity', 'N/A')}")
        print(f"   • ROA: {data.get('roa', 'N/A')}")
        print(f"   • ROE: {data.get('roe', 'N/A')}")
        
        print(f"\n🏭 COMPANY INFO:")
        print(f"   • Sector: {data.get('sector', 'N/A')}")
        print(f"   • Industry: {data.get('industry', 'N/A')}")
        print(f"   • Employees: {data.get('employees', 'N/A'):,}" if data.get('employees') else "   • Employees: N/A")
        
    else:  # Private company
        print(f"\n🔮 ESTIMATES:")
        print(f"   • Estimated Revenue: {data.get('estimated_revenue', 'N/A')}")
        print(f"   • Estimated Valuation: {data.get('estimated_valuation', 'N/A')}")
        print(f"   • Employee Count: {data.get('employee_count', 'N/A')}")
        print(f"   • Industry: {data.get('industry', 'N/A')}")
        print(f"   • Founded: {data.get('founded_year', 'N/A')}")
        
        if data.get('funding_info'):
            print(f"   • Funding Info: {data['funding_info']}")
    
    print(f"\n📖 Sources:")
    for i, source in enumerate(financial_data['sources'], 1):
        print(f"   {i}. {source['type']}: {source.get('data_points', 'Financial data')}")
        if source.get('url'):
            print(f"      URL: {source['url']}")
    
    print(f"\n🕒 Last Updated: {data['last_updated']}")
    print(f"{'='*60}")

# Test function
if __name__ == "__main__":
    # You can get a free Alpha Vantage API key from: https://www.alphavantage.co/support/#api-key
    # For testing, you can leave it as None to use only yfinance
    company = input("Enter company name: ").strip()
    financial_researcher = FinancialSnapshot(alpha_vantage_key=None)
    data = financial_researcher.research_company_financials(company)
    display_financial_snapshot(data)

    