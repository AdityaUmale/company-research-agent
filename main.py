import argparse
import json
from langchain_openai import ChatOpenAI
from langchain.agents import create_react_agent, AgentExecutor
from langchain.prompts import PromptTemplate
from langchain.tools import Tool

from tools.company_overview import research_company_overview
from tools.financial_snapshot import FinancialSnapshot
from tools.news import research_company_news, analyze_news_sentiment, structure_research_data
from tools.social_media_research import SocialMediaResearcher

def main():
    parser = argparse.ArgumentParser(description="Company Research Agent")
    parser.add_argument("--company", required=True, help="Company name to research")
    parser.add_argument("--openai-api-key", required=True, help="OpenAI API key")
    args = parser.parse_args()

    llm = ChatOpenAI(temperature=0, model="gpt-4", openai_api_key=args.openai_api_key)

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
            func=lambda company: structure_research_data(company, "", research_company_news(company), analyze_news_sentiment(research_company_news(company))),
            description="Research company news and sentiment"
        ),
        Tool(
            name="SocialMediaResearch",
            func=lambda company: SocialMediaResearcher(company).research_all_platforms(),
            description="Research social media presence"
        )
    ]

    prompt = PromptTemplate.from_template(
        "Answer the following questions as best you can. You have access to the following tools:\n\n{tools}\n\nUse the following format:\n\nQuestion: the input question you must answer\nThought: you should always think about what to do\nAction: the action to take, should be one of [{tool_names}]\nAction Input: the input to the action\nObservation: the result of the action\n... (this Thought/Action/Action Input/Observation can repeat N times)\nThought: I now know the final answer\nFinal Answer: the final answer to the original input question\n\nBegin!\n\nQuestion: Research the company {input} and provide a structured JSON report with overview, financials, news, and social media.\nThought:{agent_scratchpad}"
    )

    agent = create_react_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

    result = agent_executor.invoke({"input": args.company})

    # Structure the output
    structured_result = json.loads(result['output'])  # Assuming the final answer is JSON
    print(json.dumps(structured_result, indent=2))

if __name__ == "__main__":
    main()