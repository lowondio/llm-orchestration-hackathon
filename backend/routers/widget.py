from flask import Blueprint, request, jsonify, current_app
from flask_cors import cross_origin
from models.graph import GraphSchema
from routers.langgraph_compiler_agentic import AgenticLangGraphCompiler
from utils.logger import ExecutionLogger
from database import db
from pydantic import BaseModel
from typing import Optional
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import SystemMessage, HumanMessage

router = Blueprint('widget', __name__)

# Global checkpointer cache: one MemorySaver per graph_id
# This ensures conversation memory persists across widget requests
_widget_checkpointer_cache = {}

class WidgetChatRequest(BaseModel):
    message: str
    session_id: str

@router.route('/widget/chat/<graph_id>', methods=['POST', 'OPTIONS'])
@cross_origin(origins='*', methods=['POST', 'OPTIONS'], allow_headers=['Content-Type'])
def widget_chat(graph_id: str):
    """
    Public widget chat endpoint.
    Accepts messages from embedded chat widgets and returns AI responses.
    Uses session_id as thread_id for conversation memory.
    """

    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        return '', 204

    try:
        # Parse request payload
        payload = request.get_json() or {}

        print(f"\n{'='*60}")
        print(f"WIDGET CHAT: {graph_id}")
        print(f"{'='*60}")
        print(f"Payload: {payload}")
        print()

        # Validate request
        try:
            chat_request = WidgetChatRequest(**payload)
        except Exception as e:
            print(f"[WARN] Invalid widget chat request: {str(e)}")
            return jsonify({"error": "Invalid request format", "details": str(e)}), 400

        user_input = chat_request.message
        session_id = chat_request.session_id
        thread_id = session_id  # Use session_id as thread_id for conversation memory

        print(f"User Input: {user_input}")
        print(f"Session ID: {session_id}")
        print(f"Thread ID: {thread_id}")
        print()

        # Load graph from database
        graph_data = db.get_graph(graph_id)
        if not graph_data:
            print(f"[ERROR] Graph {graph_id} not found")
            return jsonify({"error": "Agent not found"}), 404

        # Parse graph schema
        graph_schema = GraphSchema(**graph_data)

        # Get SocketIO instance and create logger
        socketio = current_app.config.get('SOCKETIO')
        logger = ExecutionLogger(socketio, graph_id) if socketio else None

        if logger:
            logger.info(f"Widget message received", {
                "graph_id": graph_id,
                "session_id": session_id,
                "thread_id": thread_id,
                "input": user_input
            })

        # Get or create persistent checkpointer for this graph
        if graph_id not in _widget_checkpointer_cache:
            _widget_checkpointer_cache[graph_id] = MemorySaver()
            print(f"[INFO] Created new MemorySaver for widget graph {graph_id}")
        else:
            print(f"[INFO] Reusing existing MemorySaver for widget graph {graph_id}")

        # Compile to Agentic LangGraph with logger and shared checkpointer
        compiler = AgenticLangGraphCompiler(graph_schema, logger=logger, checkpointer=_widget_checkpointer_cache[graph_id])
        compiled_graph = compiler.compile()

        if logger:
            logger.info(f"Agentic graph compiled, executing with memory...")
            trigger_node = compiler._find_trigger_node()
            if trigger_node:
                logger.info(f"Trigger node started: Widget Message", {
                    "node_id": trigger_node.id,
                    "status": "running"
                })
                logger.success(f"Trigger node completed", {
                    "node_id": trigger_node.id,
                    "status": "success"
                })

        # Create initial state
        llm_node = compiler._find_llm_node()

        # Check if this is a new conversation by inspecting checkpointer state
        config = {"configurable": {"thread_id": thread_id}}

        # Get existing state from checkpointer if available
        try:
            existing_state = compiled_graph.get_state(config)
            is_new_conversation = not existing_state.values.get("messages")
        except:
            is_new_conversation = True

        # Create initial state with system prompt only for new conversations
        if is_new_conversation:
            system_prompt = llm_node.data.systemPrompt or "You are a helpful assistant."

            # Add instruction to prevent tool call leakage in responses
            enhanced_prompt = system_prompt + "\n\nIMPORTANT: When you need to use a tool, use the proper tool calling mechanism. Never include tool call JSON or function call syntax in your text responses to users. Only provide natural language responses."

            initial_state = {
                "messages": [
                    SystemMessage(content=enhanced_prompt),
                    HumanMessage(content=user_input)
                ],
                "input": user_input,
                "output": "",
                "current_node": ""
            }
            print(f"[INFO] New widget conversation started for thread {thread_id}")
        else:
            # For existing conversations, only add the new user message
            initial_state = {
                "messages": [HumanMessage(content=user_input)],
                "input": user_input,
                "output": "",
                "current_node": ""
            }
            print(f"[INFO] Continuing widget conversation for thread {thread_id}")

        # Execute with thread_id for conversation memory
        result = compiled_graph.invoke(initial_state, config=config)

        output_text = result.get("output", "No response generated")

        print()
        print(f"{'='*60}")
        print("WIDGET EXECUTION COMPLETE")
        print(f"{'='*60}")
        print(f"Output: {output_text}")
        print()

        if logger:
            logger.success(f"Widget execution completed", {"output": output_text})

        return jsonify({
            "response": output_text,
            "session_id": session_id
        }), 200

    except Exception as e:
        print(f"\n[Widget Chat Error] {str(e)}")
        import traceback
        traceback.print_exc()

        # Try to log error via WebSocket
        try:
            socketio = current_app.config.get('SOCKETIO')
            if socketio:
                logger = ExecutionLogger(socketio, graph_id)
                logger.error(f"Widget chat failed: {str(e)}")
        except:
            pass

        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500
