import { memo } from 'react';
import { Handle, Position, NodeProps, useReactFlow } from 'reactflow';
import { useGraphStore } from '../../store/graphStore';
import { Trash2, Send, FileText } from 'lucide-react';

export const ActionNode = memo(({ id, data }: NodeProps) => {
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

  const getActionIcon = () => {
    switch (data.actionType) {
      case 'http_post':
        return <Send className="w-4 h-4 text-orange-300" />;
      default:
        return <FileText className="w-4 h-4 text-orange-300" />;
    }
  };

  const getActionLabel = () => {
    switch (data.actionType) {
      case 'http_post':
        return 'HTTP POST';
      default:
        return 'Log Output';
    }
  };

  return (
    <div
      onClick={handleClick}
      className={`bg-gradient-to-br from-orange-600 to-orange-800 rounded-lg shadow-lg border-2 border-orange-400 min-w-[200px] cursor-pointer hover:shadow-xl transition-shadow relative group ${getStatusClass()}`}
    >
      <Handle type="target" position={Position.Top} className="w-3 h-3 !bg-orange-400" />

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

      <div className="px-4 py-3 border-b border-orange-400/30">
        <div className="flex items-center gap-2">
          <Send className="w-4 h-4 text-orange-300" />
          <h3 className="text-white font-semibold text-sm">Action</h3>
        </div>
      </div>

      <div className="p-4">
        <div className="flex items-center gap-2">
          {getActionIcon()}
          <span className="text-sm text-white font-medium">{getActionLabel()}</span>
        </div>

        {data.actionType === 'http_post' && data.config && (
          <div className="mt-2 bg-orange-900/30 border border-orange-400/30 rounded px-2 py-1.5">
            <p className="text-xs text-orange-200 truncate" title={data.config}>
              {data.config}
            </p>
          </div>
        )}
      </div>

      <Handle type="source" position={Position.Bottom} className="w-3 h-3 !bg-orange-400" />
    </div>
  );
});

ActionNode.displayName = 'ActionNode';
