from flask_socketio import SocketIO, emit
from typing import Optional
from datetime import datetime

class ExecutionLogger:
    """Logger that emits execution logs via WebSocket"""

    def __init__(self, socketio: SocketIO, graph_id: str):
        self.socketio = socketio
        self.graph_id = graph_id
        self.room = f"graph_{graph_id}"

    def log(self, level: str, message: str, data: Optional[dict] = None):
        """Emit a log message to the WebSocket room"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message,
            "graph_id": self.graph_id
        }

        if data:
            log_entry["data"] = data

        # Emit to the specific graph room
        self.socketio.emit('log', log_entry, room=self.room)

        # Also print to console
        print(f"[{level.upper()}] {message}")

    def info(self, message: str, data: Optional[dict] = None):
        self.log("info", message, data)

    def success(self, message: str, data: Optional[dict] = None):
        self.log("success", message, data)

    def warning(self, message: str, data: Optional[dict] = None):
        self.log("warning", message, data)

    def error(self, message: str, data: Optional[dict] = None):
        self.log("error", message, data)

    def debug(self, message: str, data: Optional[dict] = None):
        self.log("debug", message, data)
