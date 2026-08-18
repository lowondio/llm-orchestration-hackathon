import { memo } from 'react';
import { Handle, Position, NodeProps, useReactFlow } from 'reactflow';
import { useGraphStore } from '../../store/graphStore';
import { Trash2, Wrench, Search, Calculator, Globe } from 'lucide-react';

export const ToolNode = memo(({ id, data }: NodeProps) => {
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

  const getToolIcon = () => {
    switch (data.toolType) {
      case 'web_search':
        return <Search className="w-4 h-4 text-blue-300" />;
      case 'calculator':
        return <Calculator className="w-4 h-4 text-blue-300" />;
      case 'api_fetcher':
        return <Globe className="w-4 h-4 text-blue-300" />;
      default:
        return <Wrench className="w-4 h-4 text-blue-300" />;
    }
  };

  const getToolLabel = () => {
    switch (data.toolType) {
      case 'web_search':
        return 'Web Search';
      case 'calculator':
        return 'Calculator';
      case 'api_fetcher':
        return 'API Fetcher';
      default:
        return 'Tool';
    }
  };

  return (
    <div
      onClick={handleClick}
      className={`bg-gradient-to-br from-blue-600 to-blue-800 rounded-lg shadow-lg border-2 border-blue-400 min-w-[200px] cursor-pointer hover:shadow-xl transition-shadow relative group ${getStatusClass()}`}
    >
      {/* Tool nodes are "spokes" - they only OUTPUT to the LLM hub, no input handle */}

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

      <div className="px-4 py-3 border-b border-blue-400/30">
        <div className="flex items-center gap-2">
          <Wrench className="w-4 h-4 text-blue-300" />
          <h3 className="text-white font-semibold text-sm">Tool (Spoke)</h3>
        </div>
      </div>

      <div className="p-4">
        <div className="flex items-center gap-2">
          {getToolIcon()}
          <span className="text-sm text-white font-medium">{getToolLabel()}</span>
        </div>

        {data.toolType === 'api_fetcher' && data.config && (
          <div className="mt-2 bg-blue-900/30 border border-blue-400/30 rounded px-2 py-1.5">
            <p className="text-xs text-blue-200 truncate" title={data.config}>
              {data.config}
            </p>
          </div>
        )}
      </div>

      {/* Only source handle - connects to LLM's tools_in */}
      <Handle
        type="source"
        position={Position.Right}
        id="tool_out"
        className="w-3 h-3 !bg-blue-400"
      />
    </div>
  );
});

ToolNode.displayName = 'ToolNode';
