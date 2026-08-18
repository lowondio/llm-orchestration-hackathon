from flask import Blueprint, request, jsonify, current_app
from models.graph import GraphSchema, DeployResponse
from routers.graph_builder import GraphBuilder
from routers.langgraph_compiler_agentic import AgenticLangGraphCompiler
from utils.logger import ExecutionLogger
from database import db
import uuid
import json
from typing import Dict

router = Blueprint('deploy', __name__)

# In-memory storage for deployed graphs
from langgraph.checkpoint.memory import MemorySaver
from datetime import datetime
deployed_graphs: Dict[str, GraphSchema] = {}
checkpointers: Dict[str, MemorySaver] = {}

def get_checkpointer(graph_id: str) -> MemorySaver:
    if graph_id not in checkpointers:
        checkpointers[graph_id] = MemorySaver()
    return checkpointers[graph_id]

@router.route('/deploy', methods=['POST'])
def deploy_agent():
    try:
        # Parse incoming JSON
        data = request.get_json()

        # Check if graph_id is provided (for saved graphs)
        provided_graph_id = data.get('graph_id')

        # Validate with Pydantic
        graph = GraphSchema(**data)

        print("\n" + "="*60)
        print("DEPLOYING AGENT")
        print("="*60)
        print(f"Nodes: {len(graph.nodes)}")
        print(f"Edges: {len(graph.edges)}")
        if provided_graph_id:
            print(f"Using provided graph_id: {provided_graph_id}")
        print()

        # Build and validate graph
        builder = GraphBuilder(graph)
        validation = builder.validate_graph()

        if not validation['valid']:
            return jsonify({
                "status": "error",
                "errors": validation['errors'],
                "warnings": validation['warnings']
            }), 400

        # Build execution plan
        print("EXECUTION PLAN:")
        print("-" * 60)
        execution_plan = builder.build_execution_plan()
        print("-" * 60)
        print()

        if validation['warnings']:
            print("WARNINGS:")
            for warning in validation['warnings']:
                print(f"  - {warning}")
            print()

        # Use provided graph_id or generate new one
        graph_id = provided_graph_id if provided_graph_id else str(uuid.uuid4())
        deployed_graphs[graph_id] = graph

        # Save to database for webhook access
        db.save_graph(graph_id, data)

        print(f"Agent compiled successfully!")
        print(f"Graph ID: {graph_id}")
        print("="*60 + "\n")

        # Return success response
        response = DeployResponse(
            status="success",
            graph_id=graph_id,
            execution_order=execution_plan,
            message="Agent compiled successfully"
        )

        return jsonify(response.dict()), 200

    except ValueError as e:
        print(f"Validation Error: {str(e)}\n")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400
    except Exception as e:
        print(f"Error: {str(e)}\n")
        return jsonify({
            "status": "error",
            "message": f"Internal server error: {str(e)}"
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

        # Get SocketIO instance and create logger
        socketio = current_app.config.get('SOCKETIO')
        logger = ExecutionLogger(socketio, graph_id) if socketio else None

        if logger:
            logger.info(f"Starting graph execution", {"graph_id": graph_id, "input": user_input})

        # Compile to Agentic LangGraph with logger
        compiler = AgenticLangGraphCompiler(
            graph_schema, 
            logger=logger, 
            checkpointer=get_checkpointer(graph_id),
            socketio=socketio
        )
        compiled_graph = compiler.compile()

        if logger:
            logger.info(f"Agentic graph compiled successfully, starting execution...")
            trigger_node = compiler._find_trigger_node()
            if trigger_node:
                logger.info(f"Trigger node started: {trigger_node.data.label}", {
                    "node_id": trigger_node.id,
                    "status": "running"
                })
                logger.success(f"Trigger node completed", {
                    "node_id": trigger_node.id,
                    "status": "success"
                })

        # Create initial state with proper message structure
        llm_node = compiler._find_llm_node()
        initial_state = compiler.create_initial_state(user_input, llm_node)

        # Execute the graph
        config = {"configurable": {"thread_id": f"manual_{graph_id}"}}
        result = compiled_graph.invoke(initial_state, config=config)

        # Check if graph execution was interrupted by human-in-the-loop approval node
        state = compiled_graph.get_state(config)
        if "hitl" in state.next:
            hitl_node = compiler._find_hitl_node()
            hitl_message = hitl_node.data.hitlMessage or "Approve this action?"
            hitl_timeout = hitl_node.data.hitlTimeout
            
            # Find the last message content to show the user what LLM proposed
            last_message_content = ""
            for msg in reversed(state.values.get("messages", [])):
                if msg.content:
                    last_message_content = msg.content
                    break
                    
            if socketio:
                socketio.emit("hitl_interrupt", {
                    "graph_id": graph_id,
                    "thread_id": config["configurable"]["thread_id"],
                    "node_id": hitl_node.id,
                    "message": hitl_message,
                    "timeout": hitl_timeout,
                    "llm_output": last_message_content
                }, room=f"graph_{graph_id}")
                
                # Update node status in frontend
                socketio.emit("log", {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": "warning",
                    "message": f"Paused for human approval: {hitl_message}",
                    "graph_id": graph_id,
                    "data": {
                        "node_id": hitl_node.id,
                        "status": "waiting"
                    }
                }, room=f"graph_{graph_id}")

            return jsonify({
                "status": "paused",
                "graph_id": graph_id,
                "thread_id": config["configurable"]["thread_id"],
                "node_id": hitl_node.id,
                "message": hitl_message,
                "llm_output": last_message_content,
                "timeout": hitl_timeout
            }), 200

        print()
        print(f"{'='*60}")
        print("EXECUTION COMPLETE")
        print(f"{'='*60}")
        print(f"Final Output: {result.get('output', 'No output')}")
        print()

        if logger:
            logger.success(f"Graph execution completed", {"output": result.get('output', 'No output')})

        # Serialize result (exclude non-JSON-serializable message objects)
        serializable_result = {
            "input": result.get("input", ""),
            "output": result.get("output", "No output generated"),
            "current_node": result.get("current_node", ""),
            "message_count": len(result.get("messages", []))
        }

        return jsonify({
            "status": "success",
            "graph_id": graph_id,
            "result": serializable_result,
            "output": result.get("output", "No output generated")
        }), 200

    except Exception as e:
        print(f"\n[Execution Error] {str(e)}")
        import traceback
        traceback.print_exc()

        # Try to log error via WebSocket
        try:
            socketio = current_app.config.get('SOCKETIO')
            if socketio:
                logger = ExecutionLogger(socketio, graph_id)
                logger.error(f"Execution failed: {str(e)}")
        except:
            pass

        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@router.route('/webhook/<graph_id>', methods=['POST'])
def webhook_trigger(graph_id: str):
    """
    Webhook endpoint to trigger graph execution.
    Accepts any JSON payload and passes it to the graph.
    """
    try:
        # Get JSON payload from webhook
        payload = request.get_json() or {}

        print(f"\n{'='*60}")
        print(f"WEBHOOK TRIGGERED: {graph_id}")
        print(f"{'='*60}")
        print(f"Payload: {payload}")
        print()

        # Try to get from memory first
        graph_schema = deployed_graphs.get(graph_id)

        # If not in memory, load from database
        if not graph_schema:
            graph_data = db.get_graph(graph_id)
            if not graph_data:
                return jsonify({
                    "status": "error",
                    "message": f"Graph {graph_id} not found"
                }), 404

            # Parse and store in memory
            graph_schema = GraphSchema(**graph_data)
            deployed_graphs[graph_id] = graph_schema

        # Get SocketIO instance and create logger
        socketio = current_app.config.get('SOCKETIO')
        logger = ExecutionLogger(socketio, graph_id) if socketio else None

        if logger:
            logger.info(f"Webhook triggered", {"graph_id": graph_id, "payload": payload})

        # Compile to Agentic LangGraph with logger
        compiler = AgenticLangGraphCompiler(
            graph_schema, 
            logger=logger, 
            checkpointer=get_checkpointer(graph_id),
            socketio=socketio
        )
        compiled_graph = compiler.compile()

        if logger:
            logger.info(f"Agentic graph compiled successfully, starting execution...")

        # Execute the graph with webhook payload
        # Convert payload to string for initial input
        user_input = payload.get("message") or payload.get("input") or json.dumps(payload)

        # Create initial state with proper message structure
        llm_node = compiler._find_llm_node()
        initial_state = compiler.create_initial_state(user_input, llm_node)

        config = {"configurable": {"thread_id": f"webhook_{graph_id}"}}
        result = compiled_graph.invoke(initial_state, config=config)

        # Check if graph execution was interrupted by human-in-the-loop approval node
        state = compiled_graph.get_state(config)
        if "hitl" in state.next:
            hitl_node = compiler._find_hitl_node()
            hitl_message = hitl_node.data.hitlMessage or "Approve this action?"
            hitl_timeout = hitl_node.data.hitlTimeout
            
            # Find the last message content to show the user what LLM proposed
            last_message_content = ""
            for msg in reversed(state.values.get("messages", [])):
                if msg.content:
                    last_message_content = msg.content
                    break
                    
            if socketio:
                socketio.emit("hitl_interrupt", {
                    "graph_id": graph_id,
                    "thread_id": config["configurable"]["thread_id"],
                    "node_id": hitl_node.id,
                    "message": hitl_message,
                    "timeout": hitl_timeout,
                    "llm_output": last_message_content
                }, room=f"graph_{graph_id}")
                
                # Update node status in frontend
                socketio.emit("log", {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": "warning",
                    "message": f"Paused for human approval: {hitl_message}",
                    "graph_id": graph_id,
                    "data": {
                        "node_id": hitl_node.id,
                        "status": "waiting"
                    }
                }, room=f"graph_{graph_id}")

            return jsonify({
                "status": "paused",
                "graph_id": graph_id,
                "thread_id": config["configurable"]["thread_id"],
                "node_id": hitl_node.id,
                "message": hitl_message,
                "llm_output": last_message_content,
                "timeout": hitl_timeout
            }), 200

        print()
        print(f"{'='*60}")
        print("WEBHOOK EXECUTION COMPLETE")
        print(f"{'='*60}")
        print(f"Final Output: {result.get('output', 'No output')}")
        print()

        if logger:
            logger.success(f"Webhook execution completed", {"output": result.get('output', 'No output')})

        # Serialize result (exclude non-JSON-serializable message objects)
        serializable_result = {
            "input": result.get("input", ""),
            "output": result.get("output", "No output generated"),
            "current_node": result.get("current_node", ""),
            "message_count": len(result.get("messages", []))
        }

        return jsonify({
            "status": "success",
            "graph_id": graph_id,
            "result": serializable_result,
            "output": result.get("output", "No output generated")
        }), 200

    except Exception as e:
        print(f"\n[Webhook Error] {str(e)}")
        import traceback
        traceback.print_exc()

        # Try to log error via WebSocket
        try:
            socketio = current_app.config.get('SOCKETIO')
            if socketio:
                logger = ExecutionLogger(socketio, graph_id)
                logger.error(f"Webhook execution failed: {str(e)}")
        except:
            pass

        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@router.route('/run/<graph_id>/resume', methods=['POST'])
def resume_graph(graph_id: str):
    """Resume a paused graph execution after human approval/rejection"""
    try:
        if graph_id not in deployed_graphs:
            return jsonify({
                "status": "error",
                "message": f"Graph {graph_id} not found"
            }), 404

        data = request.get_json() or {}
        thread_id = data.get("thread_id")
        approved = data.get("approved", False)

        if not thread_id:
            return jsonify({
                "status": "error",
                "message": "thread_id is required to resume execution"
            }), 400

        # Get the graph schema
        graph_schema = deployed_graphs[graph_id]

        # Get SocketIO instance and create logger
        socketio = current_app.config.get('SOCKETIO')
        logger = ExecutionLogger(socketio, graph_id) if socketio else None

        if logger:
            logger.info(f"Resuming graph {graph_id} (thread: {thread_id}). Approved: {approved}")

        # Compile graph (which uses the memory checkpointer)
        checkpointer = get_checkpointer(graph_id)
        compiler = AgenticLangGraphCompiler(
            graph_schema, 
            logger=logger, 
            checkpointer=checkpointer, 
            socketio=socketio
        )
        compiled_graph = compiler.compile()

        # Update HITL node status in UI
        hitl_node = compiler._find_hitl_node()
        if socketio and hitl_node:
            socketio.emit("log", {
                "timestamp": datetime.utcnow().isoformat(),
                "level": "info",
                "message": f"Resuming execution: approved={approved}",
                "graph_id": graph_id,
                "data": {
                    "node_id": hitl_node.id,
                    "status": "success" if approved else "error"
                }
            }, room=f"graph_{graph_id}")

        if not approved:
            if logger:
                logger.error("Execution rejected by user")
            return jsonify({
                "status": "rejected",
                "graph_id": graph_id,
                "message": "Execution rejected by user"
            }), 200

        # Resume the graph
        config = {"configurable": {"thread_id": thread_id}}
        result = compiled_graph.invoke(None, config=config)

        # Check if it paused again
        state = compiled_graph.get_state(config)
        if "hitl" in state.next:
            hitl_node = compiler._find_hitl_node()
            hitl_message = hitl_node.data.hitlMessage or "Approve this action?"
            hitl_timeout = hitl_node.data.hitlTimeout
            
            last_message_content = ""
            for msg in reversed(state.values.get("messages", [])):
                if msg.content:
                    last_message_content = msg.content
                    break
                    
            if socketio:
                socketio.emit("hitl_interrupt", {
                    "graph_id": graph_id,
                    "thread_id": thread_id,
                    "node_id": hitl_node.id,
                    "message": hitl_message,
                    "timeout": hitl_timeout,
                    "llm_output": last_message_content
                }, room=f"graph_{graph_id}")

            return jsonify({
                "status": "paused",
                "graph_id": graph_id,
                "thread_id": thread_id,
                "node_id": hitl_node.id,
                "message": hitl_message,
                "llm_output": last_message_content,
                "timeout": hitl_timeout
            }), 200

        if logger:
            logger.success(f"Graph execution completed after resume", {"output": result.get('output', 'No output')})

        serializable_result = {
            "input": result.get("input", ""),
            "output": result.get("output", "No output generated"),
            "current_node": result.get("current_node", ""),
            "message_count": len(result.get("messages", []))
        }

        return jsonify({
            "status": "success",
            "graph_id": graph_id,
            "result": serializable_result,
            "output": result.get("output", "No output generated")
        }), 200

    except Exception as e:
        print(f"\n[Resume Error] {str(e)}")
        import traceback
        traceback.print_exc()

        try:
            socketio = current_app.config.get('SOCKETIO')
            if socketio:
                logger = ExecutionLogger(socketio, graph_id)
                logger.error(f"Resume failed: {str(e)}")
        except:
            pass

        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
