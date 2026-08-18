import { DragEvent } from 'react';
import { Zap, Brain, Wrench, Send, Database, Bot, UserCheck } from 'lucide-react';

const nodeTypes = [
  {
    type: 'trigger',
    label: 'Trigger',
    icon: Zap,
    color: 'from-green-500 to-green-600',
    description: 'Start workflow',
  },
  {
    type: 'llm',
    label: 'LLM Model',
    icon: Brain,
    color: 'from-purple-500 to-purple-600',
    description: 'AI processing',
  },
  {
    type: 'tool',
    label: 'Tool',
    icon: Wrench,
    color: 'from-blue-500 to-blue-600',
    description: 'Execute tool',
  },
  {
    type: 'rag',
    label: 'Knowledge Base',
    icon: Database,
    color: 'from-teal-500 to-teal-600',
    description: 'RAG context search',
  },
  {
    type: 'agent',
    label: 'Specialist Agent',
    icon: Bot,
    color: 'from-indigo-500 to-indigo-600',
    description: 'Worker specialist',
  },
  {
    type: 'hitl',
    label: 'Human Approval',
    icon: UserCheck,
    color: 'from-amber-500 to-amber-600',
    description: 'Human gatekeeper',
  },
  {
    type: 'action',
    label: 'Action',
    icon: Send,
    color: 'from-orange-500 to-orange-600',
    description: 'Perform action',
  },
];

export const Sidebar = () => {
  const onDragStart = (event: DragEvent, nodeType: string) => {
    event.dataTransfer.setData('application/reactflow', nodeType);
    event.dataTransfer.effectAllowed = 'move';
  };

  return (
    <div className="w-64 bg-gray-900 border-r border-gray-700 p-4 flex flex-col">
      <div className="mb-6">
        <h2 className="text-white font-bold text-lg mb-1">Node Library</h2>
        <p className="text-gray-400 text-xs">Drag nodes to canvas</p>
      </div>

      <div className="space-y-3 flex-1 overflow-y-auto">
        {nodeTypes.map((node) => {
          const Icon = node.icon;
          return (
            <div
              key={node.type}
              draggable
              onDragStart={(e) => onDragStart(e, node.type)}
              className={`
                bg-gradient-to-r ${node.color}
                rounded-lg p-3 cursor-grab active:cursor-grabbing
                hover:shadow-lg hover:scale-105 transition-all duration-200
                border border-white/20
              `}
            >
              <div className="flex items-center gap-3">
                <div className="bg-white/20 rounded-lg p-2">
                  <Icon className="w-5 h-5 text-white" />
                </div>
                <div className="flex-1">
                  <h3 className="text-white font-semibold text-sm">{node.label}</h3>
                  <p className="text-white/70 text-xs">{node.description}</p>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-4 pt-4 border-t border-gray-700">
        <div className="text-xs text-gray-400 space-y-1">
          <p>💡 Tip: Drag nodes onto the canvas</p>
          <p>🔗 Connect nodes by dragging from handles</p>
        </div>
      </div>
    </div>
  );
};
