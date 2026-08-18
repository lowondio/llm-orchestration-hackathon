import { memo } from 'react';
import { Handle, Position, NodeProps, useReactFlow } from 'reactflow';
import { useGraphStore } from '../../store/graphStore';
import { Trash2, Zap, Clock, Webhook, Hand, MessageCircle, Globe } from 'lucide-react';

export const TriggerNode = memo(({ id, data }: NodeProps) => {
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

  const getTriggerIcon = () => {
    switch (data.triggerType) {
      case 'webhook':
        return <Webhook className="w-4 h-4 text-green-300" />;
      case 'cron':
        return <Clock className="w-4 h-4 text-green-300" />;
      case 'interval':
        return <Clock className="w-4 h-4 text-green-300" />;
      case 'telegram':
        return <MessageCircle className="w-4 h-4 text-green-300" />;
      case 'widget':
        return <Globe className="w-4 h-4 text-green-300" />;
      default:
        return <Hand className="w-4 h-4 text-green-300" />;
    }
  };

  const getTriggerLabel = () => {
    switch (data.triggerType) {
      case 'webhook':
        return 'Webhook';
      case 'cron':
        return `Cron: ${data.cronExpression || 'Not set'}`;
      case 'interval':
        const minutes = (data.interval || 60) / 60;
        return `Every ${minutes} min${minutes !== 1 ? 's' : ''}`;
      case 'telegram':
        return 'Telegram';
      case 'widget':
        return 'Website Widget';
      default:
        return 'Manual';
    }
  };

  return (
    <div
      onClick={handleClick}
      className={`bg-gradient-to-br from-green-600 to-green-800 rounded-lg shadow-lg border-2 border-green-400 min-w-[200px] cursor-pointer hover:shadow-xl transition-shadow relative group ${getStatusClass()}`}
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

      <div className="px-4 py-3 border-b border-green-400/30">
        <div className="flex items-center gap-2">
          <Zap className="w-4 h-4 text-green-300" />
          <h3 className="text-white font-semibold text-sm">Trigger</h3>
        </div>
      </div>

      <div className="p-4">
        <div className="flex items-center gap-2">
          {getTriggerIcon()}
          <span className="text-sm text-white font-medium">{getTriggerLabel()}</span>
        </div>
      </div>

      <Handle type="source" position={Position.Bottom} className="w-3 h-3 !bg-green-400" />
    </div>
  );
});

TriggerNode.displayName = 'TriggerNode';
