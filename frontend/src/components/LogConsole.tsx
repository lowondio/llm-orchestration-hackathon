import { useState, useEffect, useRef } from 'react';
import { ChevronUp, ChevronDown, X, Terminal } from 'lucide-react';
import { io, Socket } from 'socket.io-client';
import { useGraphStore } from '../store/graphStore';

interface LogEntry {
  timestamp: string;
  level: string;
  message: string;
  graph_id: string;
  data?: any;
}

interface LogConsoleProps {
  graphId: string | null;
}

export const LogConsole = ({ graphId }: LogConsoleProps) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [socket, setSocket] = useState<Socket | null>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  // Setup WebSocket connection
  useEffect(() => {
    const newSocket = io('http://localhost:8000', {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionAttempts: 5,
    });

    newSocket.on('connect', () => {
      console.log('WebSocket connected');
    });

    newSocket.on('disconnect', () => {
      console.log('WebSocket disconnected');
    });

    newSocket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error);
    });

    newSocket.on('log', (logEntry: LogEntry) => {
      setLogs((prev) => [...prev, logEntry]);
      // Auto-expand when logs arrive
      setIsExpanded(true);

      // Update node status in graphStore if node_id and status are provided in data
      if (logEntry.data && logEntry.data.node_id && logEntry.data.status) {
        useGraphStore.getState().setNodeStatus(logEntry.data.node_id, logEntry.data.status);
      }
    });

    setSocket(newSocket);

    return () => {
      newSocket.close();
    };
  }, []); // Empty dependency array - only run once

  // Join/leave graph room when graphId changes
  useEffect(() => {
    if (socket && graphId) {
      socket.emit('join_graph', { graph_id: graphId });
      console.log(`Joined graph room: ${graphId}`);

      return () => {
        socket.emit('leave_graph', { graph_id: graphId });
      };
    }
  }, [socket, graphId]);

  const clearLogs = () => {
    setLogs([]);
  };

  const getLogColor = (level: string) => {
    switch (level) {
      case 'success':
        return 'text-green-400';
      case 'error':
        return 'text-red-400';
      case 'warning':
        return 'text-yellow-400';
      case 'info':
        return 'text-blue-400';
      case 'debug':
        return 'text-gray-400';
      default:
        return 'text-gray-300';
    }
  };

  const getLogPrefix = (level: string) => {
    switch (level) {
      case 'success':
        return '✓';
      case 'error':
        return '✗';
      case 'warning':
        return '⚠';
      case 'info':
        return 'ℹ';
      case 'debug':
        return '⚙';
      default:
        return '•';
    }
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    }) + '.' + date.getMilliseconds().toString().padStart(3, '0');
  };

  return (
    <div
      className={`fixed bottom-0 left-0 right-0 bg-gray-900 border-t border-gray-700 transition-all duration-300 z-50 ${
        isExpanded ? 'h-80' : 'h-10'
      }`}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-gray-800 border-b border-gray-700">
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-green-400" />
          <span className="text-sm font-semibold text-gray-200">Execution Logs</span>
          {logs.length > 0 && (
            <span className="text-xs text-gray-400">({logs.length})</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={clearLogs}
            className="p-1 hover:bg-gray-700 rounded transition-colors"
            title="Clear logs"
          >
            <X className="w-4 h-4 text-gray-400" />
          </button>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-1 hover:bg-gray-700 rounded transition-colors"
            title={isExpanded ? 'Collapse' : 'Expand'}
          >
            {isExpanded ? (
              <ChevronDown className="w-4 h-4 text-gray-400" />
            ) : (
              <ChevronUp className="w-4 h-4 text-gray-400" />
            )}
          </button>
        </div>
      </div>

      {/* Log content */}
      {isExpanded && (
        <div className="h-[calc(100%-40px)] overflow-y-auto bg-black p-4 font-mono text-sm">
          {logs.length === 0 ? (
            <div className="text-gray-500 text-center py-8">
              No logs yet. Execute a graph to see logs here.
            </div>
          ) : (
            <div className="space-y-1">
              {logs.map((log, index) => (
                <div key={index} className="flex gap-2">
                  <span className="text-gray-600 select-none">
                    [{formatTimestamp(log.timestamp)}]
                  </span>
                  <span className={`${getLogColor(log.level)} select-none`}>
                    {getLogPrefix(log.level)}
                  </span>
                  <span className={getLogColor(log.level)}>{log.message}</span>
                  {log.data && (
                    <span className="text-gray-500 text-xs">
                      {JSON.stringify(log.data)}
                    </span>
                  )}
                </div>
              ))}
              <div ref={logsEndRef} />
            </div>
          )}
        </div>
      )}
    </div>
  );
};
