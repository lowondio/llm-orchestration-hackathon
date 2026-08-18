import { useState, useEffect } from 'react';
import { X, Trash2, Download } from 'lucide-react';
import { listGraphs, loadGraph, deleteGraph } from '../api/client';
import { useGraphStore } from '../store/graphStore';

interface SavedGraph {
  id: string;
  name: string;
  description: string;
}

interface MyAgentsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const MyAgentsModal = ({ isOpen, onClose }: MyAgentsModalProps) => {
  const [graphs, setGraphs] = useState<SavedGraph[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { setNodes, setEdges, setCurrentGraphId } = useGraphStore();

  useEffect(() => {
    if (isOpen) {
      fetchGraphs();
    }
  }, [isOpen]);

  const fetchGraphs = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await listGraphs();
      if (response.success) {
        setGraphs(response.graphs);
      } else {
        setError('Failed to load graphs');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load graphs');
    } finally {
      setLoading(false);
    }
  };

  const handleLoadGraph = async (graphId: string) => {
    try {
      const response = await loadGraph(graphId);
      if (response.success) {
        const { config, id } = response.graph;
        setNodes(config.nodes || []);
        setEdges(config.edges || []);
        setCurrentGraphId(id);
        onClose();
      } else {
        setError('Failed to load graph');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load graph');
    }
  };

  const handleDeleteGraph = async (graphId: string, _e: React.MouseEvent) => {
    _e.stopPropagation();
    if (!confirm('Are you sure you want to delete this graph?')) {
      return;
    }

    try {
      const response = await deleteGraph(graphId);
      if (response.success) {
        setGraphs(graphs.filter(g => g.id !== graphId));
      } else {
        setError('Failed to delete graph');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to delete graph');
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-lg shadow-2xl w-full max-w-2xl max-h-[80vh] flex flex-col border border-gray-700">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-700">
          <h2 className="text-xl font-bold text-white">My Agents</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading && (
            <div className="text-center text-gray-400 py-8">
              Loading graphs...
            </div>
          )}

          {error && (
            <div className="bg-red-900 bg-opacity-20 border border-red-700 text-red-400 px-4 py-3 rounded-lg mb-4">
              {error}
            </div>
          )}

          {!loading && graphs.length === 0 && (
            <div className="text-center text-gray-400 py-8">
              No saved graphs yet. Create and save your first agent!
            </div>
          )}

          {!loading && graphs.length > 0 && (
            <div className="space-y-3">
              {graphs.map((graph) => (
                <div
                  key={graph.id}
                  onClick={() => handleLoadGraph(graph.id)}
                  className="bg-gray-900 border border-gray-700 rounded-lg p-4 hover:border-purple-500 transition-all cursor-pointer group"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <h3 className="text-white font-semibold text-lg group-hover:text-purple-400 transition-colors">
                        {graph.name}
                      </h3>
                      {graph.description && (
                        <p className="text-gray-400 text-sm mt-1">
                          {graph.description}
                        </p>
                      )}
                      <p className="text-gray-500 text-xs mt-2">
                        ID: {graph.id.slice(0, 8)}...
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleLoadGraph(graph.id)}
                        className="p-2 text-blue-400 hover:text-blue-300 hover:bg-gray-800 rounded transition-colors"
                        title="Load graph"
                      >
                        <Download className="w-5 h-5" />
                      </button>
                      <button
                        onClick={(e) => handleDeleteGraph(graph.id, e)}
                        className="p-2 text-red-400 hover:text-red-300 hover:bg-gray-800 rounded transition-colors"
                        title="Delete graph"
                      >
                        <Trash2 className="w-5 h-5" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-gray-700">
          <button
            onClick={onClose}
            className="w-full px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
