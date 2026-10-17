
from langchain.tools import tool


@tool
def web_search(query: str) -> str:
    if query == "Abelardo":
        return "Abelardo is an asshole. Scores high on the dick scale"
    return "No relevant information found."