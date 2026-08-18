import { memo } from 'react';
import { Handle, Position, NodeProps, useReactFlow } from 'reactflow';
import { useGraphStore } from '../../store/graphStore';
import { Trash2, Database, FileText } from 'lucide-react';

export const RAGNode = memo(({ id, data }: NodeProps) => {
  const { deleteElements } = useReactFlow();
  const setSelectedNodeId = useGraphStore((state) => state.setSelectedNodeId);
  const status = useGraphStore((state) => state.nodeStatuses[id]) || 'idle';

  const getStatusClass = () => {
    switch (status) {
      case 'running':
        return 'node-running';
      case 'success':
        return 'node-success';
      case 'error':
        return 'node-error';
      default:
        return '';
    }
  };

  const handleDelete = () => {
    deleteElements({ nodes: [{ id }] });
  };

  const handleClick = () => {
    setSelectedNodeId(id);
  };

  const ragFiles: Array<{ id: string; filename: string; size: number }> = data.ragFiles || [];
  const ragName: string = data.ragName || 'Knowledge Base';

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div
      onClick={handleClick}
      className={`bg-gradient-to-br from-teal-600 to-teal-800 rounded-lg shadow-lg border-2 border-teal-400 min-w-[220px] cursor-pointer hover:shadow-xl transition-shadow relative group ${getStatusClass()}`}
    >
      {/* Delete button - appears on hover */}
      <button
        onClick={(e) => {
          e.stopPropagation();
          handleDelete();
        }}
        className="absolute -top-2 -right-2 w-6 h-6 bg-red-500 hover:bg-red-600 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity z-10"
        title="Delete node"
      >
        <Trash2 className="w-3 h-3 text-white" />
      </button>

      {/* Header */}
      <div className="px-4 py-3 border-b border-teal-400/30">
        <div className="flex items-center gap-2">
          <Database className="w-4 h-4 text-teal-300" />
          <h3 className="text-white font-semibold text-sm">Knowledge Base</h3>
        </div>
      </div>

      {/* Body */}
      <div className="p-4 space-y-2">
        {/* RAG Name */}
        <div className="flex items-center gap-2">
          <Database className="w-3.5 h-3.5 text-teal-300 shrink-0" />
          <span className="text-sm text-white font-medium truncate max-w-[150px]" title={ragName}>
            {ragName}
          </span>
        </div>

        {/* File count pill */}
        <div className="flex items-center gap-1.5 mt-1">
          <FileText className="w-3 h-3 text-teal-300" />
          {ragFiles.length > 0 ? (
            <span className="text-xs text-teal-200">
              {ragFiles.length} file{ragFiles.length !== 1 ? 's' : ''} indexed
            </span>
          ) : (
            <span className="text-xs text-teal-300/60 italic">No files yet — click to configure</span>
          )}
        </div>

        {/* Quick file preview (first 2 files) */}
        {ragFiles.length > 0 && (
          <div className="space-y-1 mt-1">
            {ragFiles.slice(0, 2).map((f) => (
              <div key={f.id} className="bg-teal-900/40 border border-teal-400/20 rounded px-2 py-1 flex items-center gap-2">
                <FileText className="w-3 h-3 text-teal-300 shrink-0" />
                <span className="text-xs text-teal-200 truncate flex-1" title={f.filename}>{f.filename}</span>
                <span className="text-xs text-teal-400 shrink-0">{formatSize(f.size)}</span>
              </div>
            ))}
            {ragFiles.length > 2 && (
              <p className="text-xs text-teal-400 text-center">+{ragFiles.length - 2} more…</p>
            )}
          </div>
        )}

        {/* Status indicator */}
        {status === 'running' && (
          <div className="flex items-center gap-1.5 mt-1">
            <div className="w-2 h-2 bg-yellow-400 rounded-full animate-pulse" />
            <span className="text-xs text-yellow-300">Searching knowledge base…</span>
          </div>
        )}
        {status === 'success' && (
          <div className="flex items-center gap-1.5 mt-1">
            <div className="w-2 h-2 bg-green-400 rounded-full" />
            <span className="text-xs text-green-300">Search complete</span>
          </div>
        )}
      </div>

      {/* Only source handle - connects to LLM's tools_in */}
      <Handle
        type="source"
        position={Position.Right}
        id="rag_out"
        className="w-3 h-3 !bg-teal-400"
      />
    </div>
  );
});

RAGNode.displayName = 'RAGNode';
