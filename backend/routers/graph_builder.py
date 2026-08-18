from typing import List, Dict, Set
from models.graph import GraphSchema, Node, Edge

class GraphBuilder:
    def __init__(self, graph: GraphSchema):
        self.graph = graph
        self.nodes_map = {node.id: node for node in graph.nodes}
        self.edges_map = self._build_edges_map()

    def _build_edges_map(self) -> Dict[str, List[str]]:
        """Build adjacency list from edges"""
        edges_map = {}
        for edge in self.graph.edges:
            if edge.source not in edges_map:
                edges_map[edge.source] = []
            edges_map[edge.source].append(edge.target)
        return edges_map

    def find_trigger_nodes(self) -> List[Node]:
        """Find all trigger nodes (entry points)"""
        return [node for node in self.graph.nodes if node.type == 'trigger']

    def topological_sort(self) -> List[str]:
        """
        Perform topological sort to determine execution order.
        Returns list of node IDs in execution order.
        """
        # Find nodes with no incoming edges (triggers)
        incoming_count = {node.id: 0 for node in self.graph.nodes}
        for edge in self.graph.edges:
            incoming_count[edge.target] += 1

        # Start with nodes that have no incoming edges
        queue = [node_id for node_id, count in incoming_count.items() if count == 0]
        execution_order = []

        while queue:
            current = queue.pop(0)
            execution_order.append(current)

            # Reduce incoming count for neighbors
            if current in self.edges_map:
                for neighbor in self.edges_map[current]:
                    incoming_count[neighbor] -= 1
                    if incoming_count[neighbor] == 0:
                        queue.append(neighbor)

        # Check for cycles
        if len(execution_order) != len(self.graph.nodes):
            raise ValueError("Graph contains cycles - cannot determine execution order")

        return execution_order

    def build_execution_plan(self) -> List[str]:
        """
        Build human-readable execution plan for Hub-and-Spoke architecture.
        """
        plan = []

        # Find the hub (LLM node)
        llm_nodes = [n for n in self.graph.nodes if n.type == 'llm']
        if not llm_nodes:
            plan.append("ERROR: No LLM hub found")
            return plan

        llm_node = llm_nodes[0]

        # Find trigger
        trigger_nodes = self.find_trigger_nodes()
        if trigger_nodes:
            trigger = trigger_nodes[0]
            trigger_desc = self._describe_node(1, trigger)
            plan.append(f"Step 1: {trigger_desc}")
            print(f"Step 1: {trigger_desc}")

        # Find tools connected to LLM
        tool_nodes = []
        for edge in self.graph.edges:
            if edge.target == llm_node.id and edge.targetHandle == 'tools_in':
                source_node = self.nodes_map.get(edge.source)
                if source_node and source_node.type == 'tool':
                    tool_nodes.append(source_node)

        # Describe the agentic loop
        step_num = 2
        llm_desc = self._describe_node(step_num, llm_node)
        plan.append(f"Step {step_num}: {llm_desc}")
        print(f"Step {step_num}: {llm_desc}")

        if tool_nodes:
            step_num += 1
            tool_names = [f"{t.data.toolType}" for t in tool_nodes]
            tools_desc = f"Agentic Loop: LLM can call tools [{', '.join(tool_names)}] and reason iteratively"
            plan.append(f"Step {step_num}: {tools_desc}")
            print(f"Step {step_num}: {tools_desc}")

        # Find action
        action_nodes = []
        for edge in self.graph.edges:
            if edge.source == llm_node.id and edge.sourceHandle == 'execution_out':
                target_node = self.nodes_map.get(edge.target)
                if target_node and target_node.type == 'action':
                    action_nodes.append(target_node)

        if action_nodes:
            step_num += 1
            action = action_nodes[0]
            action_desc = self._describe_node(step_num, action)
            plan.append(f"Step {step_num}: {action_desc}")
            print(f"Step {step_num}: {action_desc}")

        return plan

    def _describe_node(self, step: int, node: Node) -> str:
        """Generate human-readable description of a node"""
        if node.type == 'trigger':
            trigger_type = node.data.triggerType or 'unknown'
            if trigger_type == 'cron':
                cron = node.data.cronExpression or 'not set'
                return f"Trigger (Cron: {cron})"
            elif trigger_type == 'interval':
                interval = node.data.interval or 60
                return f"Trigger (Every {interval} seconds)"
            elif trigger_type == 'webhook':
                return f"Trigger (Webhook)"
            else:
                return f"Trigger (Manual)"

        elif node.type == 'llm':
            model = node.data.model or 'unknown'
            prompt_preview = (node.data.systemPrompt or '')[:50]
            if len(node.data.systemPrompt or '') > 50:
                prompt_preview += '...'
            return f"LLM ({model}) with prompt: '{prompt_preview}'"

        elif node.type == 'tool':
            tool_type = node.data.toolType or 'unknown'
            return f"Tool ({tool_type})"

        elif node.type == 'action':
            action_type = node.data.actionType or 'unknown'
            return f"Action ({action_type})"

        return f"Unknown node type: {node.type}"

    def validate_graph(self) -> Dict[str, any]:
        """
        Validate Hub-and-Spoke graph structure.
        """
        errors = []
        warnings = []

        # Check for exactly ONE LLM node (the hub)
        llm_nodes = [node for node in self.graph.nodes if node.type == 'llm']
        if not llm_nodes:
            errors.append("Hub-and-Spoke architecture requires exactly one LLM node (the hub)")
        elif len(llm_nodes) > 1:
            errors.append("Only one LLM hub is allowed in Hub-and-Spoke architecture")

        # Check for trigger nodes
        triggers = self.find_trigger_nodes()
        if not triggers:
            errors.append("Graph must have at least one Trigger node")

        # Validate Hub-and-Spoke connections
        if llm_nodes:
            llm_node_id = llm_nodes[0].id

            # Check that LLM has execution_in connection from Trigger
            execution_in_edges = [
                e for e in self.graph.edges
                if e.target == llm_node_id and e.targetHandle == 'execution_in'
            ]
            if not execution_in_edges:
                warnings.append("LLM hub should have a Trigger connected to its execution_in handle (top)")

            # Check that LLM has at least one tool connected to tools_in
            tools_in_edges = [
                e for e in self.graph.edges
                if e.target == llm_node_id and e.targetHandle == 'tools_in'
            ]
            if not tools_in_edges:
                warnings.append("LLM hub has no tools connected. Consider adding Tool spokes for agentic behavior")

            # Check that LLM has execution_out connection to Action
            execution_out_edges = [
                e for e in self.graph.edges
                if e.source == llm_node_id and e.sourceHandle == 'execution_out'
            ]
            if not execution_out_edges:
                warnings.append("LLM hub should have an Action connected to its execution_out handle (bottom)")

        # Validate Tool nodes only connect to LLM's tools_in
        tool_nodes = [node for node in self.graph.nodes if node.type == 'tool']
        for tool_node in tool_nodes:
            tool_edges = [e for e in self.graph.edges if e.source == tool_node.id]
            for edge in tool_edges:
                target_node = self.nodes_map.get(edge.target)
                if not target_node or target_node.type != 'llm' or edge.targetHandle != 'tools_in':
                    errors.append(f"Tool node {tool_node.id} must connect only to LLM's tools_in handle")

        # Validate Trigger nodes only connect to LLM's execution_in
        for trigger in triggers:
            trigger_edges = [e for e in self.graph.edges if e.source == trigger.id]
            for edge in trigger_edges:
                target_node = self.nodes_map.get(edge.target)
                if not target_node or target_node.type != 'llm' or edge.targetHandle != 'execution_in':
                    errors.append(f"Trigger node {trigger.id} must connect only to LLM's execution_in handle")

        # Validate Action nodes are terminal (no outgoing edges)
        action_nodes = [node for node in self.graph.nodes if node.type == 'action']
        for action_node in action_nodes:
            action_edges = [e for e in self.graph.edges if e.source == action_node.id]
            if action_edges:
                errors.append(f"Action node {action_node.id} is terminal and should not have outgoing connections")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
