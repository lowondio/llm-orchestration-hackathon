import { create } from 'zustand';
import {
  Node,
  Edge,
  OnNodesChange,
  OnEdgesChange,
  OnConnect,
  OnNodesDelete,
  OnEdgesDelete,
  applyNodeChanges,
  applyEdgeChanges,
  addEdge,
} from 'reactflow';

export type NodeData = {
  label: string;
  [key: string]: any;
};

interface GraphState {
  nodes: Node<NodeData>[];
  edges: Edge[];
  currentGraphId: string | null;
  selectedNodeId: string | null;
  onNodesChange: OnNodesChange;
  onEdgesChange: OnEdgesChange;
  onNodesDelete: OnNodesDelete;
  onEdgesDelete: OnEdgesDelete;
  onConnect: OnConnect;
  addNode: (type: string, position: { x: number; y: number }) => void;
  updateNodeData: (nodeId: string, data: Partial<NodeData>) => void;
  setSelectedNodeId: (nodeId: string | null) => void;
  setCurrentGraphId: (graphId: string | null) => void;
  setNodes: (nodes: Node<NodeData>[]) => void;
  setEdges: (edges: Edge[]) => void;
  clearCanvas: () => void;
  nodeStatuses: Record<string, 'idle' | 'running' | 'success' | 'error' | 'waiting'>;
  setNodeStatus: (nodeId: string, status: 'idle' | 'running' | 'success' | 'error' | 'waiting') => void;
  resetNodeStatuses: () => void;
}

export const useGraphStore = create<GraphState>((set, get) => ({
  nodes: [],
  edges: [],
  currentGraphId: null,
  selectedNodeId: null,
  nodeStatuses: {},

  onNodesChange: (changes) => {
    set({
      nodes: applyNodeChanges(changes, get().nodes),
    });
  },

  onEdgesChange: (changes) => {
    set({
      edges: applyEdgeChanges(changes, get().edges),
    });
  },

  onNodesDelete: (deleted) => {
    console.log('Nodes deleted:', deleted.map(n => n.id));
    // Nodes are already removed by onNodesChange, this is just for logging/side effects
  },

  onEdgesDelete: (deleted) => {
    console.log('Edges deleted:', deleted.map(e => e.id));
    // Edges are already removed by onEdgesChange, this is just for logging/side effects
  },

  onConnect: (connection) => {
    // Hub-and-Spoke validation
    const { nodes } = get();
    const sourceNode = nodes.find(n => n.id === connection.source);
    const targetNode = nodes.find(n => n.id === connection.target);

    if (!sourceNode || !targetNode) {
      console.warn('Invalid connection: source or target node not found');
      return;
    }

    // Validation rules for Hub-and-Spoke architecture
    const sourceType = sourceNode.type;
    const targetType = targetNode.type;
    const targetHandle = connection.targetHandle;

    // Rule 1: Tool, RAG, and Agent nodes can connect to LLM or Agent nodes' tools_in handle
    if (sourceType === 'tool' || sourceType === 'rag' || sourceType === 'agent') {
      if ((targetType !== 'llm' && targetType !== 'agent') || targetHandle !== 'tools_in') {
        console.warn('Tool/RAG/Agent nodes can only connect to LLM\'s or Agent\'s tools_in handle');
        alert('⚠️ Tool, RAG, and Agent nodes must connect to the LLM or Agent\'s left handle (tools_in)');
        return;
      }
    }

    // Rule 2: Trigger nodes can ONLY connect to LLM's execution_in handle
    if (sourceType === 'trigger') {
      if (targetType !== 'llm' || targetHandle !== 'execution_in') {
        console.warn('Trigger nodes can only connect to LLM\'s execution_in handle');
        alert('⚠️ Trigger nodes must connect to the LLM\'s top handle (execution_in)');
        return;
      }
    }

    // Rule 3: LLM's execution_out can connect to Action or HITL nodes
    if (sourceType === 'llm' && connection.sourceHandle === 'execution_out') {
      if (targetType !== 'action' && targetType !== 'hitl') {
        console.warn('LLM execution_out can only connect to Action or HITL nodes');
        alert('⚠️ LLM\'s bottom handle (execution_out) must connect to an Action or HITL node');
        return;
      }
    }

    // Rule 3b: HITL's execution_out can ONLY connect to Action nodes
    if (sourceType === 'hitl' && connection.sourceHandle === 'execution_out') {
      if (targetType !== 'action') {
        console.warn('HITL execution_out can only connect to Action nodes');
        alert('⚠️ HITL\'s bottom handle (execution_out) must connect to an Action node');
        return;
      }
    }

    // Rule 4: Action nodes should not have outgoing connections (terminal nodes)
    if (sourceType === 'action') {
      console.warn('Action nodes are terminal and should not have outgoing connections');
      alert('⚠️ Action nodes are terminal - they cannot connect to other nodes');
      return;
    }

    // Rule 5: Only ONE trigger can connect to LLM's execution_in
    if (sourceType === 'trigger' && targetHandle === 'execution_in') {
      const existingTriggerConnection = get().edges.find(
        e => e.target === connection.target && e.targetHandle === 'execution_in'
      );
      if (existingTriggerConnection) {
        console.warn('LLM already has a trigger connection');
        alert('⚠️ LLM can only have ONE trigger connection');
        return;
      }
    }

    // All validations passed - add the edge
    set({
      edges: addEdge(connection, get().edges),
    });
  },

  addNode: (type, position) => {
    const newNode: Node<NodeData> = {
      id: `${type}-${Date.now()}`,
      type,
      position,
      data: {
        label: type === 'agent' ? 'Specialist Agent' : type === 'hitl' ? 'Human Approval' : type,
        // Set default values based on node type
        ...(type === 'tool' && { toolType: 'web_search' }),
        ...(type === 'action' && { actionType: 'log' }),
        ...(type === 'llm' && { model: 'gpt-4o-mini' }),
        ...(type === 'trigger' && { triggerType: 'manual' }),
        ...(type === 'rag' && { ragName: 'Knowledge Base', chunkSize: 500, chunkOverlap: 50, topK: 3, ragFiles: [] }),
        ...(type === 'agent' && { agentModel: 'gpt-4o-mini', agentRole: 'specialist', agentSystemPrompt: 'You are a helpful specialist assistant.' }),
        ...(type === 'hitl' && { hitlMessage: 'Do you approve this action?', hitlTimeout: 60 }),
      },
    };

    set({
      nodes: [...get().nodes, newNode],
    });
  },

  updateNodeData: (nodeId, data) => {
    set({
      nodes: get().nodes.map((node) =>
        node.id === nodeId
          ? { ...node, data: { ...node.data, ...data } }
          : node
      ),
    });
  },

  setSelectedNodeId: (nodeId) => {
    set({ selectedNodeId: nodeId });
  },

  setCurrentGraphId: (graphId) => {
    set({ currentGraphId: graphId });
  },

  setNodes: (nodes) => {
    set({ nodes });
  },

  setEdges: (edges) => {
    set({ edges });
  },

  setNodeStatus: (nodeId, status) => {
    set({
      nodeStatuses: {
        ...get().nodeStatuses,
        [nodeId]: status,
      },
    });
  },

  resetNodeStatuses: () => {
    set({
      nodeStatuses: {},
    });
  },

  clearCanvas: () => {
    set({
      nodes: [],
      edges: [],
      currentGraphId: null,
      nodeStatuses: {},
    });
  },
}));
