from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
from flask_socketio import SocketIO, join_room, leave_room
from datetime import datetime
from routers.deploy import router as deploy_router
from routers.graphs import router as graphs_router
from routers.telegram import router as telegram_router
from routers.widget import router as widget_router
from routers.rag import router as rag_router
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
import os

# Load environment variables
load_dotenv()

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.config['JSON_AS_ASCII'] = False  # Disable ASCII-only JSON encoding

# Configure CORS properly
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    },
    r"/static/*": {
        "origins": "*"
    }
})

# Initialize SocketIO with proper CORS
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='threading',
    logger=True,
    engineio_logger=True,
    ping_timeout=60,
    ping_interval=25
)

# Initialize APScheduler
scheduler = BackgroundScheduler()
scheduler.start()

# Store socketio and scheduler instances globally for access in routers
app.config['SOCKETIO'] = socketio
app.config['SCHEDULER'] = scheduler

# Register blueprints
app.register_blueprint(deploy_router, url_prefix='/api')
app.register_blueprint(graphs_router, url_prefix='/api')
app.register_blueprint(telegram_router, url_prefix='/api')
app.register_blueprint(widget_router, url_prefix='/api')
app.register_blueprint(rag_router, url_prefix='/api')

@app.route('/')
def root():
    return jsonify({"message": "AI Agent Builder API is running"})

@app.route('/api/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "AI Agent Builder API"
    })

# WebSocket event handlers
@socketio.on('connect')
def handle_connect():
    print(f"[SocketIO] Client connected - SID: {request.sid}")
    socketio.emit('connection_status', {'status': 'connected'})

@socketio.on('disconnect')
def handle_disconnect():
    print(f"[SocketIO] Client disconnected - SID: {request.sid}")

@socketio.on('join_graph')
def handle_join_graph(data):
    """Join a room for a specific graph to receive its logs"""
    graph_id = data.get('graph_id')
    if graph_id:
        room = f"graph_{graph_id}"
        join_room(room)
        print(f"[SocketIO] Client {request.sid} joined room: {room}")
        socketio.emit('joined', {'graph_id': graph_id, 'room': room})

@socketio.on('leave_graph')
def handle_leave_graph(data):
    """Leave a graph's room"""
    graph_id = data.get('graph_id')
    if graph_id:
        room = f"graph_{graph_id}"
        leave_room(room)
        print(f"[SocketIO] Client {request.sid} left room: {room}")

if __name__ == '__main__':
    print("\n" + "="*60)
    print("AI Agent Builder - Backend Server")
    print("="*60)

    # Check API keys
    openai_key = os.getenv("OPENAI_API_KEY", "")
    nvidia_key = os.getenv("NVIDIA_API_KEY", "")

    has_openai = openai_key and not openai_key.startswith("dummy") and openai_key != "test"
    has_nvidia = nvidia_key and not nvidia_key.startswith("dummy") and nvidia_key != "test"

    if has_openai:
        print(f"[OK] OpenAI API Key loaded: {openai_key[:20]}...")
    else:
        print("[WARN] OpenAI API Key not found")

    if has_nvidia:
        print(f"[OK] Nvidia API Key loaded: {nvidia_key[:20]}...")
    else:
        print("[WARN] Nvidia API Key not found")

    if has_openai or has_nvidia:
        print("[INFO] LLM Mode: REAL (using API)")
    else:
        print("[INFO] LLM Mode: MOCK (test responses)")
        print("[INFO] To enable real LLM, see: SETUP_REAL_LLM.md")

    print("="*60 + "\n")

    try:
        socketio.run(app, host='0.0.0.0', port=8000, debug=True, allow_unsafe_werkzeug=True)
    finally:
        # Shutdown scheduler gracefully
        scheduler.shutdown()
