from flask import Blueprint, request, jsonify, current_app
from database import GraphModel, SessionLocal
from models.graph import GraphSchema
from routers.langgraph_compiler_agentic import AgenticLangGraphCompiler
from utils.logger import ExecutionLogger
import uuid
import json
import requests
import os

router = Blueprint('graphs', __name__)

def schedule_interval_trigger(graph_id: str, interval_seconds: int, graph_data: dict):
    """Schedule an interval-based trigger for a graph"""
    scheduler = current_app.config.get('SCHEDULER')
    socketio = current_app.config.get('SOCKETIO')

    if not scheduler:
        print(f"[WARN] Scheduler not available, skipping interval trigger for {graph_id}")
        return

    # Remove existing job if it exists
    try:
        scheduler.remove_job(f"graph_{graph_id}")
        print(f"[INFO] Removed existing scheduled job for graph {graph_id}")
    except:
        pass

    def execute_scheduled_graph():
        """Execute the graph on schedule"""
        try:
            print(f"\n{'='*60}")
            print(f"SCHEDULED EXECUTION: {graph_id}")
            print(f"{'='*60}\n")

            # Parse graph schema
            graph_schema = GraphSchema(**graph_data)

            # Create logger
            logger = ExecutionLogger(socketio, graph_id) if socketio else None

            if logger:
                logger.info(f"Scheduled execution triggered", {"graph_id": graph_id})

            # Compile graph
            compiler = AgenticLangGraphCompiler(graph_schema, logger=logger)
            compiled_graph = compiler.compile()

            # Create initial state with default prompt
            llm_node = compiler._find_llm_node()
            user_input = "Scheduled run triggered. Use your tools to fetch data and perform your tasks."
            initial_state = compiler.create_initial_state(user_input, llm_node)

            # Execute
            config = {"configurable": {"thread_id": f"scheduled_{graph_id}"}}
            result = compiled_graph.invoke(initial_state, config=config)

            print(f"\n{'='*60}")
            print("SCHEDULED EXECUTION COMPLETE")
            print(f"{'='*60}")
            print(f"Output: {result.get('output', 'No output')}\n")

            if logger:
                logger.success(f"Scheduled execution completed", {"output": result.get('output', 'No output')})

        except Exception as e:
            print(f"[ERROR] Scheduled execution failed for {graph_id}: {str(e)}")
            if socketio:
                try:
                    logger = ExecutionLogger(socketio, graph_id)
                    logger.error(f"Scheduled execution failed: {str(e)}")
                except:
                    pass

    # Add job to scheduler
    scheduler.add_job(
        execute_scheduled_graph,
        'interval',
        seconds=interval_seconds,
        id=f"graph_{graph_id}",
        replace_existing=True
    )

    print(f"[INFO] Scheduled interval trigger for graph {graph_id} every {interval_seconds} seconds")

def remove_scheduled_trigger(graph_id: str):
    """Remove a scheduled trigger for a graph"""
    scheduler = current_app.config.get('SCHEDULER')

    if not scheduler:
        return

    try:
        scheduler.remove_job(f"graph_{graph_id}")
        print(f"[INFO] Removed scheduled job for graph {graph_id}")
    except:
        pass

def register_telegram_webhook(graph_id: str, bot_token: str):
    """Register Telegram webhook for a bot"""
    try:
        # Get base URL from environment or use default
        base_url = os.getenv("WEBHOOK_BASE_URL", "http://localhost:8000")
        webhook_url = f"{base_url}/api/telegram/webhook/{graph_id}"

        # Call Telegram API to set webhook
        telegram_api_url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
        response = requests.post(
            telegram_api_url,
            json={"url": webhook_url},
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            if result.get("ok"):
                print(f"[INFO] Telegram webhook registered: {webhook_url}")
                return True
            else:
                print(f"[WARN] Telegram webhook registration failed: {result.get('description')}")
                return False
        else:
            print(f"[WARN] Telegram API returned status {response.status_code}")
            return False

    except Exception as e:
        print(f"[ERROR] Failed to register Telegram webhook: {str(e)}")
        return False

def unregister_telegram_webhook(bot_token: str):
    """Unregister Telegram webhook for a bot"""
    try:
        telegram_api_url = f"https://api.telegram.org/bot{bot_token}/deleteWebhook"
        response = requests.post(telegram_api_url, timeout=10)

        if response.status_code == 200:
            print(f"[INFO] Telegram webhook unregistered")
            return True
        else:
            print(f"[WARN] Failed to unregister Telegram webhook")
            return False

    except Exception as e:
        print(f"[ERROR] Failed to unregister Telegram webhook: {str(e)}")
        return False

@router.route('/graphs', methods=['POST'])
def save_graph():
    """Save a new graph or update existing one"""
    try:
        data = request.json
        graph_id = data.get('id') or str(uuid.uuid4())
        name = data.get('name', 'Untitled Agent')
        description = data.get('description', '')
        config = data.get('config', {})

        db = SessionLocal()
        try:
            # Check if graph exists
            existing = db.query(GraphModel).filter_by(id=graph_id).first()

            if existing:
                # Update existing
                existing.name = name
                existing.description = description
                existing.config = json.dumps(config)
            else:
                # Create new
                graph = GraphModel(
                    id=graph_id,
                    name=name,
                    description=description,
                    config=json.dumps(config)
                )
                db.add(graph)

            db.commit()

            # Check for interval trigger
            try:
                graph_schema = GraphSchema(**config)
                trigger_nodes = [n for n in graph_schema.nodes if n.type == "trigger"]

                if trigger_nodes:
                    trigger_node = trigger_nodes[0]
                    trigger_type = trigger_node.data.triggerType

                    if trigger_type == "interval":
                        interval_seconds = trigger_node.data.interval or 60
                        schedule_interval_trigger(graph_id, interval_seconds, config)
                    elif trigger_type == "telegram":
                        # Register Telegram webhook
                        bot_token = trigger_node.data.botToken
                        if bot_token:
                            register_telegram_webhook(graph_id, bot_token)
                        else:
                            print(f"[WARN] Telegram trigger without bot token")
                        # Remove any existing scheduled job
                        remove_scheduled_trigger(graph_id)
                    else:
                        # Remove any existing scheduled job if trigger type changed
                        remove_scheduled_trigger(graph_id)
            except Exception as e:
                print(f"[WARN] Failed to process trigger: {str(e)}")

            return jsonify({
                'success': True,
                'id': graph_id,
                'message': 'Graph saved successfully'
            }), 200

        finally:
            db.close()

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@router.route('/graphs', methods=['GET'])
def list_graphs():
    """List all saved graphs"""
    try:
        db = SessionLocal()
        try:
            graphs = db.query(GraphModel).all()
            return jsonify({
                'success': True,
                'graphs': [
                    {
                        'id': g.id,
                        'name': g.name,
                        'description': g.description
                    }
                    for g in graphs
                ]
            }), 200
        finally:
            db.close()

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@router.route('/graphs/<graph_id>', methods=['GET'])
def get_graph(graph_id):
    """Load a specific graph by ID"""
    try:
        db = SessionLocal()
        try:
            graph = db.query(GraphModel).filter_by(id=graph_id).first()

            if not graph:
                return jsonify({
                    'success': False,
                    'error': 'Graph not found'
                }), 404

            return jsonify({
                'success': True,
                'graph': graph.to_dict()
            }), 200

        finally:
            db.close()

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@router.route('/graphs/<graph_id>', methods=['PUT'])
def update_graph(graph_id):
    """Update an existing graph (prevents duplicates)"""
    try:
        data = request.json
        name = data.get('name', 'Untitled Agent')
        description = data.get('description', '')
        config = data.get('config', {})

        db = SessionLocal()
        try:
            graph = db.query(GraphModel).filter_by(id=graph_id).first()

            if not graph:
                return jsonify({
                    'success': False,
                    'error': 'Graph not found'
                }), 404

            # Update existing graph
            graph.name = name
            graph.description = description
            graph.config = json.dumps(config)
            db.commit()

            # Check for interval trigger
            try:
                graph_schema = GraphSchema(**config)
                trigger_nodes = [n for n in graph_schema.nodes if n.type == "trigger"]

                if trigger_nodes:
                    trigger_node = trigger_nodes[0]
                    trigger_type = trigger_node.data.triggerType

                    if trigger_type == "interval":
                        interval_seconds = trigger_node.data.interval or 60
                        schedule_interval_trigger(graph_id, interval_seconds, config)
                    elif trigger_type == "telegram":
                        # Register Telegram webhook
                        bot_token = trigger_node.data.botToken
                        if bot_token:
                            register_telegram_webhook(graph_id, bot_token)
                        else:
                            print(f"[WARN] Telegram trigger without bot token")
                        # Remove any existing scheduled job
                        remove_scheduled_trigger(graph_id)
                    else:
                        # Remove any existing scheduled job if trigger type changed
                        remove_scheduled_trigger(graph_id)
                else:
                    # No trigger node, remove any existing scheduled job
                    remove_scheduled_trigger(graph_id)
            except Exception as e:
                print(f"[WARN] Failed to process trigger: {str(e)}")

            return jsonify({
                'success': True,
                'id': graph_id,
                'message': 'Graph updated successfully'
            }), 200

        finally:
            db.close()

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@router.route('/graphs/<graph_id>', methods=['DELETE'])
def delete_graph(graph_id):
    """Delete a graph by ID"""
    try:
        db = SessionLocal()
        try:
            graph = db.query(GraphModel).filter_by(id=graph_id).first()

            if not graph:
                return jsonify({
                    'success': False,
                    'error': 'Graph not found'
                }), 404

            db.delete(graph)
            db.commit()

            # Remove any scheduled job
            remove_scheduled_trigger(graph_id)

            return jsonify({
                'success': True,
                'message': 'Graph deleted successfully'
            }), 200

        finally:
            db.close()

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
