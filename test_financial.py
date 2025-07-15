# test_financial.py
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.financial_snapshot import FinancialSnapshot, display_financial_snapshot

def test_financial_module():
    """Test the financial snapshot module"""
    
    # Initialize the financial researcher
    # You can add your Alpha Vantage API key here for better ticker search
    financial_researcher = FinancialSnapshot(alpha_vantage_key=None)
    
    # Test companies
    test_companies = [
        "Tesla, Inc.",      # Public company
        "Apple Inc.",       # Public company  
        "Microsoft Corporation",  # Public company
        "SpaceX",          # Private company
        "Stripe",          # Private company
    ]
    
    for company in test_companies:
        print(f"\n{'='*80}")
        print(f"Testing: {company}")
        print(f"{'='*80}")
        
        try:
            result = financial_researcher.research_company_financials(company)
            display_financial_snapshot(result)
        except Exception as e:
            print(f"❌ Error testing {company}: {e}")
        
        print(f"\n{'='*80}")
        input("Press Enter to continue to next company...")

if __name__ == "__main__":
    test_financial_module()