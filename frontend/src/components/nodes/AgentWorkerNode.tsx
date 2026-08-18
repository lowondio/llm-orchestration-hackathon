import { memo } from 'react';
import { Handle, Position, NodeProps, useReactFlow } from 'reactflow';
import { useGraphStore } from '../../store/graphStore';
import { Trash2, Bot } from 'lucide-react';

export const AgentWorkerNode = memo(({ id, data }: NodeProps) => {
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

  const getModelDisplayName = (model: string) => {
    const modelMap: Record<string, string> = {
      'gpt-4o': 'GPT-4o',
      'gpt-4o-mini': 'GPT-4o-mini',
      'meta/llama-3.1-405b-instruct': 'Llama 3.1 405B',
      'meta/llama-3.1-70b-instruct': 'Llama 3.1 70B',
      'meta/llama-3.1-8b-instruct': 'Llama 3.1 8B',
      'mistralai/mixtral-8x22b-instruct-v0.1': 'Mixtral 8x22B',
      'mistralai/mistral-large-2-instruct': 'Mistral Large 2',
    };
    return modelMap[model] || model;
  };

  return (
    <div
      onClick={handleClick}
      className={`bg-gradient-to-br from-indigo-600 to-indigo-800 rounded-lg shadow-lg border-2 border-indigo-400 min-w-[240px] cursor-pointer hover:shadow-xl transition-shadow relative group ${getStatusClass()}`}
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

      {/* Left target handle: tools_in - allows connecting Tools or RAG nodes to this agent */}
      <Handle
        type="target"
        position={Position.Left}
        id="tools_in"
        className="w-3 h-3 !bg-blue-400"
        style={{ top: '50%' }}
      />

      <div className="px-4 py-3 border-b border-indigo-400/30">
        <div className="flex items-center gap-2">
          <Bot className="w-4 h-4 text-indigo-300" />
          <h3 className="text-white font-semibold text-sm">Specialist Agent</h3>
        </div>
      </div>

      <div className="p-4 space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs text-indigo-200">Role:</span>
          <span className="text-sm text-white font-medium capitalize">{data.agentRole || 'specialist'}</span>
        </div>

        <div className="flex items-center justify-between">
          <span className="text-xs text-indigo-200">Model:</span>
          <span className="text-xs text-indigo-200 font-medium">{getModelDisplayName(data.agentModel || 'gpt-4o-mini')}</span>
        </div>

        {data.agentSystemPrompt && (
          <div className="bg-indigo-900/40 border border-indigo-400/20 rounded px-2 py-1.5">
            <p className="text-xs text-indigo-200 line-clamp-2">
              {data.agentSystemPrompt}
            </p>
          </div>
        )}
      </div>

      {/* Right source handle: tool_out - connects to the LLM hub's tools_in */}
      <Handle
        type="source"
        position={Position.Right}
        id="tool_out"
        className="w-3 h-3 !bg-indigo-400"
        style={{ top: '50%' }}
      />
    </div>
  );
});

AgentWorkerNode.displayName = 'AgentWorkerNode';
