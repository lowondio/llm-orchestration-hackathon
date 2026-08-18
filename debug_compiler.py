"""
Simple debug script to test the LangGraph compiler directly
"""

import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

os.environ["OPENAI_API_KEY"] = "dummy-key-for-testing"

from models.graph import GraphSchema, Node, NodeData, Edge, Position
from routers.langgraph_compiler import LangGraphCompiler

# Create a simple graph
graph_data = {
    "nodes": [
        {
            "id": "trigger-1",
            "type": "trigger",
            "position": {"x": 100, "y": 100},
            "data": {
                "label": "Manual Trigger",
                "triggerType": "manual"
            }
        },
        {
            "id": "llm-1",
            "type": "llm",
            "position": {"x": 300, "y": 100},
            "data": {
                "label": "GPT Assistant",
                "model": "gpt-3.5-turbo",
                "systemPrompt": "You are a helpful assistant."
            }
        }
    ],
    "edges": [
        {
            "id": "e1",
            "source": "trigger-1",
            "target": "llm-1"
        }
    ]
}

print("Creating graph schema...")
graph = GraphSchema(**graph_data)

print("Compiling graph...")
compiler = LangGraphCompiler(graph)
compiled_graph = compiler.compile()

print("Executing graph...")
initial_state = {"input": "What is 2+2?"}
print(f"Initial state: {initial_state}")

result = compiled_graph.invoke(initial_state)

print(f"\nResult type: {type(result)}")
print(f"Result: {result}")

if result:
    print(f"\nOutput: {result.get('output', 'No output')}")
else:
    print("\nERROR: Result is None!")
