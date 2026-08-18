from flask import Blueprint, request, jsonify
from models.graph import GraphSchema
from routers.langgraph_compiler import LangGraphCompiler
import uuid
from typing import Dict, Any

router = Blueprint('execution', __name__)

# In-memory storage for deployed graphs
deployed_graphs: Dict[str, GraphSchema] = {}

@router.route('/deploy', methods=['POST'])
def deploy_graph():
    """Deploy a graph and store it for execution"""
    try:
        data = request.get_json()
        graph = GraphSchema(**data)

        graph_id = str(uuid.uuid4())
        deployed_graphs[graph_id] = graph

        print(f"\n[Deploy] Graph {graph_id} deployed successfully")
        print(f"[Deploy] Nodes: {len(graph.nodes)}, Edges: {len(graph.edges)}")

        return jsonify({
            "status": "success",
            "graph_id": graph_id,
            "message": "Graph deployed successfully"
        }), 200

    except Exception as e:
        print(f"[Deploy Error] {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@router.route('/run/<graph_id>', methods=['POST'])
def run_graph(graph_id: str):
    """Execute a deployed graph with given input"""
    try:
        if graph_id not in deployed_graphs:
            return jsonify({
                "status": "error",
                "message": f"Graph {graph_id} not found"
            }), 404

        # Get input from request
        data = request.get_json() or {}
        user_input = data.get("input", "Hello, world!")

        print(f"\n{'='*60}")
        print(f"EXECUTING GRAPH: {graph_id}")
        print(f"{'='*60}")
        print(f"Input: {user_input}")
        print()

        # Get the graph schema
        graph_schema = deployed_graphs[graph_id]

        # Compile to LangGraph
        compiler = LangGraphCompiler(graph_schema)
        compiled_graph = compiler.compile()

        # Execute the graph
        initial_state = {"input": user_input}
        result = compiled_graph.invoke(initial_state)

        print()
        print(f"{'='*60}")
        print("EXECUTION COMPLETE")
        print(f"{'='*60}")
        print(f"Final Output: {result.get('output', 'No output')}")
        print()

        return jsonify({
            "status": "success",
            "graph_id": graph_id,
            "result": result,
            "output": result.get("output", "No output generated")
        }), 200

    except Exception as e:
        print(f"\n[Execution Error] {str(e)}")
        import traceback
        traceback.print_exc()

        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@router.route('/graphs', methods=['GET'])
def list_graphs():
    """List all deployed graphs"""
    graphs_info = []
    for graph_id, graph in deployed_graphs.items():
        graphs_info.append({
            "graph_id": graph_id,
            "nodes_count": len(graph.nodes),
            "edges_count": len(graph.edges),
            "created_at": graph.created_at.isoformat()
        })

    return jsonify({
        "status": "success",
        "graphs": graphs_info
    }), 200
