import requests
import json

# Test data: Simple graph with Trigger -> LLM -> Tool
test_graph = {
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
                "systemPrompt": "You are a helpful assistant. Respond concisely."
            }
        },
        {
            "id": "tool-1",
            "type": "tool",
            "position": {"x": 500, "y": 100},
            "data": {
                "label": "Web Search",
                "toolType": "web_search"
            }
        }
    ],
    "edges": [
        {
            "id": "e1",
            "source": "trigger-1",
            "target": "llm-1"
        },
        {
            "id": "e2",
            "source": "llm-1",
            "target": "tool-1"
        }
    ]
}

BASE_URL = "http://localhost:8000/api"

def test_deploy():
    print("\n" + "="*60)
    print("TEST 1: Deploy Graph")
    print("="*60)

    response = requests.post(f"{BASE_URL}/deploy", json=test_graph)
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}")

    if response.status_code == 200:
        return result.get("graph_id")
    return None

def test_run(graph_id):
    print("\n" + "="*60)
    print("TEST 2: Run Graph")
    print("="*60)

    test_input = {
        "input": "Tell me about artificial intelligence"
    }

    response = requests.post(f"{BASE_URL}/run/{graph_id}", json=test_input)
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}")

def test_list_graphs():
    print("\n" + "="*60)
    print("TEST 3: List Graphs")
    print("="*60)

    response = requests.get(f"{BASE_URL}/graphs")
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}")

if __name__ == "__main__":
    try:
        # Test deployment
        graph_id = test_deploy()

        if graph_id:
            # Test execution
            test_run(graph_id)

            # Test listing
            test_list_graphs()
        else:
            print("\nDeployment failed, skipping other tests")

    except requests.exceptions.ConnectionError:
        print("\nError: Could not connect to server at http://localhost:8000")
        print("Make sure the Flask server is running with: python backend/main.py")
    except Exception as e:
        print(f"\nError: {str(e)}")
