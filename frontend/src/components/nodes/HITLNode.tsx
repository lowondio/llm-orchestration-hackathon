import { memo } from 'react';
import { Handle, Position, NodeProps, useReactFlow } from 'reactflow';
import { useGraphStore } from '../../store/graphStore';
import { Trash2, UserCheck, ShieldAlert } from 'lucide-react';

export const HITLNode = memo(({ id, data }: NodeProps) => {
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
      case 'waiting':
        return 'border-amber-500 animate-pulse bg-amber-950/80';
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

  return (
    <div
      onClick={handleClick}
      className={`bg-gradient-to-br from-amber-600 to-amber-800 rounded-lg shadow-lg border-2 border-amber-400 min-w-[200px] cursor-pointer hover:shadow-xl transition-shadow relative group ${getStatusClass()}`}
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

      {/* Top Handle: execution_in - connects from LLM node */}
      <Handle
        type="target"
        position={Position.Top}
        id="execution_in"
        className="w-3 h-3 !bg-orange-400"
        style={{ left: '50%' }}
      />

      <div className="px-4 py-3 border-b border-amber-400/30">
        <div className="flex items-center gap-2">
          <UserCheck className="w-4 h-4 text-amber-300" />
          <h3 className="text-white font-semibold text-sm">Human Approval</h3>
        </div>
      </div>

      <div className="p-4 space-y-2">
        <div className="flex items-center gap-1.5 text-xs text-amber-200">
          <ShieldAlert className="w-3.5 h-3.5" />
          <span>Gatekeeper / Interrupter</span>
        </div>

        {data.hitlMessage && (
          <div className="bg-amber-900/40 border border-amber-400/20 rounded px-2 py-1.5">
            <p className="text-xs text-amber-100 truncate" title={data.hitlMessage}>
              {data.hitlMessage}
            </p>
          </div>
        )}

        <div className="flex items-center justify-between text-[11px] text-amber-300">
          <span>Timeout:</span>
          <span>{data.hitlTimeout ? `${data.hitlTimeout}s` : 'None'}</span>
        </div>
      </div>

      {/* Bottom Handle: execution_out - connects to Action node */}
      <Handle
        type="source"
        position={Position.Bottom}
        id="execution_out"
        className="w-3 h-3 !bg-orange-400"
        style={{ left: '50%' }}
      />
    </div>
  );
});

HITLNode.displayName = 'HITLNode';
