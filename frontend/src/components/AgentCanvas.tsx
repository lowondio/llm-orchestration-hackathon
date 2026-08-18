import { useCallback, DragEvent, useMemo } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  BackgroundVariant,
  NodeTypes,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { useGraphStore } from '../store/graphStore';
import { LLMNode } from './nodes/LLMNode';
import { ToolNode } from './nodes/ToolNode';
import { TriggerNode } from './nodes/TriggerNode';
import { ActionNode } from './nodes/ActionNode';
import { RAGNode } from './nodes/RAGNode';
import { AgentWorkerNode } from './nodes/AgentWorkerNode';
import { HITLNode } from './nodes/HITLNode';

export const AgentCanvas = () => {
  const {
    nodes,
    edges,
    onNodesChange,
    onEdgesChange,
    onNodesDelete,
    onEdgesDelete,
    onConnect,
    addNode,
    setSelectedNodeId
  } = useGraphStore();

  const nodeTypes: NodeTypes = useMemo(
    () => ({
      llm: LLMNode,
      tool: ToolNode,
      trigger: TriggerNode,
      action: ActionNode,
      rag: RAGNode,
      agent: AgentWorkerNode,
      hitl: HITLNode,
    }),
    []
  );

  const onDragOver = useCallback((event: DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event: DragEvent) => {
      event.preventDefault();

      const type = event.dataTransfer.getData('application/reactflow');
      if (!type) return;

      const reactFlowBounds = (event.target as HTMLElement)
        .closest('.react-flow')
        ?.getBoundingClientRect();

      if (!reactFlowBounds) return;

      const position = {
        x: event.clientX - reactFlowBounds.left - 140,
        y: event.clientY - reactFlowBounds.top - 50,
      };

      addNode(type, position);
    },
    [addNode]
  );

  const onSelectionChange = useCallback(
    ({ nodes }: { nodes: any[] }) => {
      if (nodes.length === 1) {
        setSelectedNodeId(nodes[0].id);
      } else {
        setSelectedNodeId(null);
      }
    },
    [setSelectedNodeId]
  );

  return (
    <div className="w-full h-full bg-gray-950">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodesDelete={onNodesDelete}
        onEdgesDelete={onEdgesDelete}
        onConnect={onConnect}
        onDragOver={onDragOver}
        onDrop={onDrop}
        onSelectionChange={onSelectionChange}
        nodeTypes={nodeTypes}
        fitView
        className="bg-gray-950"
        deleteKeyCode={['Backspace', 'Delete']}
        defaultEdgeOptions={{
          type: 'smoothstep',
          animated: true,
          style: { stroke: '#6366f1', strokeWidth: 2 },
        }}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={20}
          size={1}
          color="#374151"
        />
        <Controls className="bg-gray-800 border-gray-700" />
        <MiniMap
          className="bg-gray-800 border-gray-700"
          nodeColor={(node) => {
            switch (node.type) {
              case 'trigger':
                return '#22c55e';
              case 'llm':
                return '#a855f7';
              case 'tool':
                return '#3b82f6';
              case 'rag':
                return '#14b8a6';
              case 'action':
                return '#f97316';
              default:
                return '#6b7280';
            }
          }}
          maskColor="rgba(0, 0, 0, 0.6)"
        />
      </ReactFlow>
    </div>
  );
};
