from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import tool

# Initialize DuckDuckGo search (no API key required)
ddg_search = DuckDuckGoSearchRun()

@tool
def web_search(query: str) -> str:
    """
    Search the web using DuckDuckGo.
    Returns real search results from the internet.

    Args:
        query: The search query string

    Returns:
        Search results as a string
    """
    try:
        results = ddg_search.run(query)
        return results
    except Exception as e:
        return f"Search failed: {str(e)}"
