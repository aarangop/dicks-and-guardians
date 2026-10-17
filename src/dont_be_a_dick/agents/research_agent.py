from langchain.agents import create_agent

from dont_be_a_dick.tools.web_search import web_search

MODEL="anthropic:claude-haiku-5-5"


agent = create_agent(model=MODEL, tools=[web_search])
