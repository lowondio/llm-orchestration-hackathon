from flask import Blueprint, request, jsonify, current_app
from models.graph import GraphSchema
from routers.langgraph_compiler_agentic import AgenticLangGraphCompiler
from utils.logger import ExecutionLogger
from database import db
from pydantic import BaseModel
from typing import Optional, Dict, Any
import requests
import json
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import SystemMessage, HumanMessage

router = Blueprint('telegram', __name__)

# Global checkpointer cache: one MemorySaver per graph_id
# This ensures conversation memory persists across webhook requests
_checkpointer_cache: Dict[str, MemorySaver] = {}

# Pydantic v1 models for Telegram webhook payloads
class TelegramUser(BaseModel):
    id: int
    is_bot: bool
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None

class TelegramChat(BaseModel):
    id: int
    type: str
    title: Optional[str] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class TelegramMessage(BaseModel):
    message_id: int
    from_: Optional[TelegramUser] = None
    chat: TelegramChat
    date: int
    text: Optional[str] = None

    class Config:
        fields = {'from_': 'from'}

class TelegramUpdate(BaseModel):
    update_id: int
    message: Optional[TelegramMessage] = None

def send_telegram_message(bot_token: str, chat_id: int, text: str) -> bool:
    """Send a message via Telegram Bot API"""
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }

        print(f"[DEBUG] Sending to Telegram API: {url[:50]}...")
        print(f"[DEBUG] Chat ID: {chat_id}")
        print(f"[DEBUG] Message length: {len(text)} chars")

        response = requests.post(url, json=payload, timeout=10)

        print(f"[DEBUG] Telegram API response status: {response.status_code}")
        print(f"[DEBUG] Telegram API response: {response.text}")

        response.raise_for_status()
        return True
    except requests.exceptions.HTTPError as e:
        print(f"[ERROR] Telegram API HTTP error: {e}")
        print(f"[ERROR] Response content: {e.response.text if e.response else 'No response'}")

        # Try sending without Markdown if parse error
        if e.response and e.response.status_code == 400:
            try:
                print("[INFO] Retrying without Markdown parse mode...")
                payload_plain = {
                    "chat_id": chat_id,
                    "text": text
                }
                response = requests.post(url, json=payload_plain, timeout=10)
                response.raise_for_status()
                print("[SUCCESS] Message sent without Markdown")
                return True
            except Exception as retry_error:
                print(f"[ERROR] Retry also failed: {retry_error}")
        return False
    except requests.exceptions.Timeout as e:
        print(f"[ERROR] Telegram API timeout: {str(e)}")
        return False
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Telegram API request failed: {str(e)}")
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected error sending Telegram message: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

@router.route('/telegram/webhook/<graph_id>', methods=['POST'])
def telegram_webhook(graph_id: str):
    """
    Native Telegram webhook endpoint.
    Receives Telegram updates, executes the graph with conversation memory,
    and automatically sends the response back to the user.
    """
    try:
        # Parse Telegram update
        payload = request.get_json() or {}

        print(f"\n{'='*60}")
        print(f"TELEGRAM WEBHOOK: {graph_id}")
        print(f"{'='*60}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        print()

        # Validate Telegram update structure
        try:
            update = TelegramUpdate(**payload)
        except Exception as e:
            print(f"[WARN] Invalid Telegram update format: {str(e)}")
            return jsonify({"status": "error", "message": "Invalid Telegram update"}), 400

        # Extract message and chat_id
        if not update.message or not update.message.text:
            print("[INFO] No text message in update, ignoring")
            return jsonify({"status": "ok", "message": "No text message"}), 200

        user_input = update.message.text
        chat_id = update.message.chat.id
        thread_id = str(chat_id)  # Use chat_id as thread_id for conversation memory

        print(f"User Input: {user_input}")
        print(f"Chat ID: {chat_id}")
        print(f"Thread ID: {thread_id}")
        print()

        # Load graph from database
        graph_data = db.get_graph(graph_id)
        if not graph_data:
            print(f"[ERROR] Graph {graph_id} not found")
            return jsonify({"status": "error", "message": "Graph not found"}), 404

        # Parse graph schema
        graph_schema = GraphSchema(**graph_data)

        # Find trigger node and extract bot token
        trigger_nodes = [n for n in graph_schema.nodes if n.type == "trigger"]
        if not trigger_nodes:
            print("[ERROR] No trigger node found in graph")
            return jsonify({"status": "error", "message": "No trigger node"}), 400

        trigger_node = trigger_nodes[0]
        bot_token = trigger_node.data.botToken

        if not bot_token:
            print("[ERROR] No bot token configured in trigger node")
            return jsonify({"status": "error", "message": "No bot token configured"}), 400

        # Get SocketIO instance and create logger
        socketio = current_app.config.get('SOCKETIO')
        logger = ExecutionLogger(socketio, graph_id) if socketio else None

        if logger:
            logger.info(f"Telegram message received", {
                "graph_id": graph_id,
                "chat_id": chat_id,
                "thread_id": thread_id,
                "input": user_input
            })

        # Get or create persistent checkpointer for this graph
        if graph_id not in _checkpointer_cache:
            _checkpointer_cache[graph_id] = MemorySaver()
            print(f"[INFO] Created new MemorySaver for graph {graph_id}")
        else:
            print(f"[INFO] Reusing existing MemorySaver for graph {graph_id}")

        # Compile to Agentic LangGraph with logger and shared checkpointer
        compiler = AgenticLangGraphCompiler(graph_schema, logger=logger, checkpointer=_checkpointer_cache[graph_id])
        compiled_graph = compiler.compile()

        if logger:
            logger.info(f"Agentic graph compiled, executing with memory...")
            if trigger_node:
                logger.info(f"Trigger node started: Telegram Message", {
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
            print(f"[INFO] New conversation started for thread {thread_id}")
        else:
            # For existing conversations, only add the new user message
            initial_state = {
                "messages": [HumanMessage(content=user_input)],
                "input": user_input,
                "output": "",
                "current_node": ""
            }
            print(f"[INFO] Continuing conversation for thread {thread_id}")

        # Execute with thread_id for conversation memory
        result = compiled_graph.invoke(initial_state, config=config)

        output_text = result.get("output", "No response generated")

        print()
        print(f"{'='*60}")
        print("TELEGRAM EXECUTION COMPLETE")
        print(f"{'='*60}")
        print(f"Output: {output_text}")
        print()

        if logger:
            logger.success(f"Graph execution completed", {"output": output_text})

        # Send response back to Telegram
        send_success = send_telegram_message(bot_token, chat_id, output_text)

        if send_success:
            print(f"[SUCCESS] Response sent to Telegram chat {chat_id}")
            if logger:
                logger.success(f"Response sent to Telegram", {"chat_id": chat_id})
        else:
            print(f"[ERROR] Failed to send response to Telegram")
            if logger:
                logger.error(f"Failed to send Telegram response", {"chat_id": chat_id})

        return jsonify({
            "status": "success",
            "graph_id": graph_id,
            "chat_id": chat_id,
            "thread_id": thread_id,
            "output": output_text,
            "sent_to_telegram": send_success
        }), 200

    except Exception as e:
        print(f"\n[Telegram Webhook Error] {str(e)}")
        import traceback
        traceback.print_exc()

        # Try to log error via WebSocket
        try:
            socketio = current_app.config.get('SOCKETIO')
            if socketio:
                logger = ExecutionLogger(socketio, graph_id)
                logger.error(f"Telegram webhook failed: {str(e)}")
        except:
            pass

        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
