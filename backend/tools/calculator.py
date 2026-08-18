from langchain_core.tools import tool
import numexpr as ne

@tool
def calculator(expression: str) -> str:
    """
    Safely evaluate mathematical expressions.
    Supports basic arithmetic operations: +, -, *, /, **, sqrt, sin, cos, etc.

    Args:
        expression: Mathematical expression to evaluate (e.g., "2 + 2", "sqrt(16)", "3**2")

    Returns:
        Result of the calculation as a string
    """
    try:
        # Use numexpr for safe evaluation (no arbitrary code execution)
        result = ne.evaluate(expression)
        return f"Result: {result}"
    except Exception as e:
        return f"Calculation error: {str(e)}"
