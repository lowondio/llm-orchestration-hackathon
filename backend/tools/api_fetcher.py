from langchain_core.tools import tool
import requests
from typing import Optional

@tool
def api_fetcher(url: str, headers: Optional[str] = None) -> str:
    """
    Fetch data from an external API via HTTP GET request.

    Args:
        url: The URL to fetch data from
        headers: Optional JSON string of headers (e.g., '{"Authorization": "Bearer token"}')

    Returns:
        The response text or JSON from the API
    """
    try:
        headers_dict = {}
        if headers:
            import json
            headers_dict = json.loads(headers)

        response = requests.get(url, headers=headers_dict, timeout=30)
        response.raise_for_status()

        # Try to return JSON if possible, otherwise return text
        try:
            return str(response.json())
        except:
            return response.text

    except requests.exceptions.Timeout:
        return f"Error: Request to {url} timed out after 30 seconds"
    except requests.exceptions.RequestException as e:
        return f"Error fetching data from {url}: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"
