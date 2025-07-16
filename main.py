import argparse
import json
import os
from langchain_openai import ChatOpenAI
from langchain.agents import create_react_agent, AgentExecutor
from langchain.prompts import PromptTemplate
from langchain.tools import Tool
from dotenv import load_dotenv
import re

from tools.company_overview import research_company_overview
from tools.financial_snapshot import FinancialSnapshot
from tools.news import research_company_news, analyze_news_sentiment, structure_research_data, detect_controversies, extract_future_plans
from tools.social_media_research import SocialMediaResearcher
from tools.competitor_analysis import get_competitor_summary
from tools.customer_research import ClientResearchTool
from tools.glassdoor_research import get_glassdoor_summary
from tools.job_listing import get_job_listings

def main():
    # Load environment variables from .env file
    load_dotenv()
    # Get OpenAI API key from environment
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY not found in environment. Please set it in your .env file.")

    parser = argparse.ArgumentParser(description="Company Research Agent")
    parser.add_argument("--company", required=True, help="Company name to research")
    args = parser.parse_args()

    # The OpenAI key will be picked up from the environment
    llm = ChatOpenAI(temperature=0, model="gpt-4")

    # Define tools
    tools = [
        Tool(
            name="CompanyOverview",
            func=research_company_overview,
            description="Research company overview including description, founded, founders, etc."
        ),
        Tool(
            name="FinancialSnapshot",
            func=FinancialSnapshot().research_company_financials,
            description="Get financial snapshot of the company"
        ),
        Tool(
            name="NewsResearch",
            func=lambda company: (
                lambda news: structure_research_data(
                    company,
                    "",
                    news,
                    analyze_news_sentiment(news),
                    detect_controversies(news),
                    extract_future_plans(news)
                )
            )(research_company_news(company)),
            description="Research company news and sentiment"
        ),
        Tool(
            name="SocialMediaResearch",
            func=lambda company: SocialMediaResearcher(company).research_all_platforms(),
            description="Research social media presence"
        ),
        Tool(
            name="CompetitorAnalysis",
            func=lambda domain: get_competitor_summary(domain),
            description="Get a summary of the company's competitors by domain (e.g., example.com)"
        ),
        Tool(
            name="CustomerResearch",
            func=lambda company: ClientResearchTool().research_company_clients(company),
            description="Research company clients, customer segments, and target markets using free web resources"
        ),
        Tool(
            name="GlassdoorResearch",
            func=lambda company: get_glassdoor_summary(company),
            description="Research company reviews and ratings from Glassdoor"
        ),
        Tool(
            name="JobListing",
            func=lambda company: get_job_listings(company),
            description="Get current job listings for the company from multiple sources"
        )
    ]

    prompt = PromptTemplate.from_template(
        "Answer the following questions as best you can. You have access to the following tools:\n\n{tools}\n\nUse the following format:\n\nQuestion: the input question you must answer\nThought: you should always think about what to do\nAction: the action to take, should be one of [{tool_names}]\nAction Input: the input to the action\nObservation: the result of the action\n... (this Thought/Action/Action Input/Observation can repeat N times)\nThought: I now know the final answer\nFinal Answer: the final answer to the original input question\n\nBegin!\n\nQuestion: Research the company {input} and provide a structured JSON report with overview, financials, news, social media, competitors, customer research, glassdoor research, and job listings.\nThought:{agent_scratchpad}"
    )

    agent = create_react_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

    result = agent_executor.invoke({"input": args.company})

    # Structure the output
    output = result['output']
    # Extract the JSON part after 'Final Answer:'
    match = re.search(r'Final Answer:\s*(\{.*\})', output, re.DOTALL)
    if match:
        json_str = match.group(1)
        structured_result = json.loads(json_str)
        print(json.dumps(structured_result, indent=2))
    else:
        print("Could not find JSON in the output:")
        print(output)

if __name__ == "__main__":
    main()