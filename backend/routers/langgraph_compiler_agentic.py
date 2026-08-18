from typing import Dict, Any, List, Optional, TypedDict, Sequence
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage, ToolMessage
from langchain_core.tools import BaseTool, Tool
from models.graph import GraphSchema, Node, Edge
from tools import web_search, calculator, api_fetcher
import os
import requests
from typing_extensions import Annotated

def add_messages(left: Sequence[BaseMessage], right: Sequence[BaseMessage]) -> Sequence[BaseMessage]:
    """Merge message lists for state updates"""
    return list(left) + list(right)

class AgentState(TypedDict):
    """State object for agentic LangGraph execution - Pydantic v1 compatible"""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    input: str
    output: str
    current_node: str

class AgenticLangGraphCompiler:
    """
    Hub-and-Spoke Agentic Compiler

    Architecture:
    - Trigger -> LLM (Hub) <- Tools (Spokes)
    - LLM can loop with tools multiple times (ReAct pattern)
    - LLM -> Action (final output)
    """

    def __init__(self, graph_schema: GraphSchema, logger=None, checkpointer=None, socketio=None):
        self.graph_schema = graph_schema
        self.nodes_map = {node.id: node for node in graph_schema.nodes}
        self.edges_map = self._build_edges_map()
        self.llm_instances: Dict[str, Any] = {}
        self.logger = logger
        self.checkpointer = checkpointer if checkpointer is not None else MemorySaver()
        self.socketio = socketio

    def _build_edges_map(self) -> Dict[str, List[Edge]]:
        """Build adjacency list from edges with full edge objects"""
        edges_map = {}
        for edge in self.graph_schema.edges:
            if edge.source not in edges_map:
                edges_map[edge.source] = []
            edges_map[edge.source].append(edge)
        return edges_map

    def _find_llm_node(self) -> Optional[Node]:
        """Find the LLM hub node"""
        llm_nodes = [n for n in self.graph_schema.nodes if n.type == "llm"]
        if not llm_nodes:
            raise ValueError("No LLM node found - Hub-and-Spoke requires an LLM hub")
        if len(llm_nodes) > 1:
            raise ValueError("Multiple LLM nodes found - only one hub is allowed")
        return llm_nodes[0]

    def _find_tool_nodes_for_llm(self, llm_node_id: str) -> List[Node]:
        """Find all tool nodes connected to LLM's tools_in handle"""
        tool_nodes = []
        for edge in self.graph_schema.edges:
            if edge.target == llm_node_id and edge.targetHandle == "tools_in":
                source_node = self.nodes_map.get(edge.source)
                if source_node and source_node.type == "tool":
                    tool_nodes.append(source_node)
        return tool_nodes

    def _find_rag_nodes_for_llm(self, llm_node_id: str) -> List[Node]:
        """Find all RAG nodes connected to LLM's tools_in handle"""
        rag_nodes = []
        for edge in self.graph_schema.edges:
            if edge.target == llm_node_id and edge.targetHandle == "tools_in":
                source_node = self.nodes_map.get(edge.source)
                if source_node and source_node.type == "rag":
                    rag_nodes.append(source_node)
        return rag_nodes

    def _find_agent_nodes_for_llm(self, llm_node_id: str) -> List[Node]:
        """Find all Agent worker nodes connected to LLM's tools_in handle"""
        agent_nodes = []
        for edge in self.graph_schema.edges:
            if edge.target == llm_node_id and edge.targetHandle == "tools_in":
                source_node = self.nodes_map.get(edge.source)
                if source_node and source_node.type == "agent":
                    agent_nodes.append(source_node)
        return agent_nodes

    def _find_hitl_node(self) -> Optional[Node]:
        """Find the HITL node connected to LLM's execution_out"""
        llm_node = self._find_llm_node()
        for edge in self.graph_schema.edges:
            if edge.source == llm_node.id and edge.sourceHandle == "execution_out":
                target_node = self.nodes_map.get(edge.target)
                if target_node and target_node.type == "hitl":
                    return target_node
        return None

    def _find_trigger_node(self) -> Optional[Node]:
        """Find the trigger node connected to LLM's execution_in"""
        llm_node = self._find_llm_node()
        for edge in self.graph_schema.edges:
            if edge.target == llm_node.id and edge.targetHandle == "execution_in":
                source_node = self.nodes_map.get(edge.source)
                if source_node and source_node.type == "trigger":
                    return source_node
        return None

    def _find_action_node(self) -> Optional[Node]:
        """Find the action node connected to LLM's execution_out or via HITL node"""
        llm_node = self._find_llm_node()
        # Direct connection
        for edge in self.graph_schema.edges:
            if edge.source == llm_node.id and edge.sourceHandle == "execution_out":
                target_node = self.nodes_map.get(edge.target)
                if target_node and target_node.type == "action":
                    return target_node
        # Via HITL node
        hitl_node = self._find_hitl_node()
        if hitl_node:
            for edge in self.graph_schema.edges:
                if edge.source == hitl_node.id and edge.sourceHandle == "execution_out":
                    target_node = self.nodes_map.get(edge.target)
                    if target_node and target_node.type == "action":
                        return target_node
        return None

    def _create_langchain_tools(self, tool_nodes: List[Node]) -> List[BaseTool]:
        """Convert tool nodes to LangChain tools"""
        tools = []
        for tool_node in tool_nodes:
            tool_type = tool_node.data.toolType
            if tool_type == "web_search":
                tools.append(web_search)
                if self.logger:
                    self.logger.info(f"Registered tool: web_search", {"node_id": tool_node.id})
            elif tool_type == "calculator":
                tools.append(calculator)
                if self.logger:
                    self.logger.info(f"Registered tool: calculator", {"node_id": tool_node.id})
            elif tool_type == "api_fetcher":
                tools.append(api_fetcher)
                if self.logger:
                    self.logger.info(f"Registered tool: api_fetcher", {"node_id": tool_node.id})
            else:
                if self.logger:
                    self.logger.warning(f"Unknown tool type: {tool_type}", {"node_id": tool_node.id})
        return tools

    def _create_rag_tool(self, rag_node: Node) -> BaseTool:
        """Create a LangChain StructuredTool from a RAG node.
        
        Uses StructuredTool with an explicit args_schema so the LLM
        always passes a single 'query' string, preventing the
        'Too many arguments to single-input tool' error.
        """
        from langchain_core.tools import StructuredTool
        from pydantic import BaseModel, Field as PydanticField
        
        node_id = rag_node.id
        top_k = rag_node.data.topK or 3
        rag_name = rag_node.data.ragName or "Knowledge Base"
        clean_name = f"search_knowledge_base_{node_id.replace('-', '_')}"
        
        files_list = []
        if rag_node.data.ragFiles:
            files_list = [f["filename"] for f in rag_node.data.ragFiles]
        files_desc = f" (files: {', '.join(files_list)})" if files_list else ""
        
        description = (
            f"Search the '{rag_name}' knowledge base{files_desc} for relevant details. "
            f"Useful to answer questions using uploaded documents. "
            f"Pass a single natural-language search query string."
        )

        # Explicit input schema so the LLM never splits args
        class SearchInput(BaseModel):
            query: str = PydanticField(
                description="A natural-language search query to find relevant information in the knowledge base"
            )
        
        def search_fn(query: str) -> str:
            from utils.rag_manager import RagManager
            results = RagManager.search(node_id, query, top_k)
            if not results:
                return f"No relevant information found in the knowledge base '{rag_name}'."
            return "\n\n---\n\n".join([f"Context: {r['text']}" for r in results])
            
        return StructuredTool(
            name=clean_name,
            description=description,
            func=search_fn,
            args_schema=SearchInput
        )

    def _create_agent_tool(self, agent_node: Node) -> BaseTool:
        """Create a LangChain StructuredTool from an Agent node"""
        from langchain_core.tools import StructuredTool
        from pydantic import BaseModel, Field as PydanticField
        from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage

        node_id = agent_node.id
        agent_name = agent_node.data.label or "Specialist Agent"
        clean_name = f"call_agent_{node_id.replace('-', '_')}"
        
        role = agent_node.data.agentRole or "specialist"
        system_prompt = agent_node.data.agentSystemPrompt or "You are a helpful specialist assistant."
        description = (
            f"Delegate tasks to the '{agent_name}' ({role}). "
            f"Description/Capabilities: {system_prompt[:200]}... "
            f"Provide a specific instruction as the task."
        )

        class AgentInput(BaseModel):
            task: str = PydanticField(
                description="The task instruction to send to the specialist agent"
            )

        def agent_fn(task: str) -> str:
            if self.logger:
                self.logger.info(f"Invoking worker agent: {agent_name}", {
                    "node_id": node_id,
                    "task": task,
                    "status": "running"
                })

            if self._is_mock_mode():
                resp = f"[Specialist Agent '{agent_name}' ({role})]"
                if "sales" in agent_name.lower() or "sales" in system_prompt.lower():
                    resp += "\nHere is the sales pricing/return info: We offer standard pricing at $49/mo, enterprise at $199/mo. Refund period is 14 days."
                elif "support" in agent_name.lower() or "support" in system_prompt.lower():
                    resp += "\nFor technical support: Please check the logs in backend/utils. Standard server runs on port 8000."
                else:
                    resp += f"\nProcessed task: '{task}' using system prompt '{system_prompt[:50]}...'"
                
                if self.logger:
                    self.logger.success(f"Worker agent completed (mock): {resp[:100]}...", {
                        "node_id": node_id,
                        "status": "success"
                    })
                return resp

            try:
                # Find tools and RAGs connected to this agent node
                tool_nodes = []
                rag_nodes = []
                for edge in self.graph_schema.edges:
                    if edge.target == node_id and edge.targetHandle == "tools_in":
                        source_node = self.nodes_map.get(edge.source)
                        if source_node:
                            if source_node.type == "tool":
                                tool_nodes.append(source_node)
                            elif source_node.type == "rag":
                                rag_nodes.append(source_node)

                worker_tools = []
                worker_tools.extend(self._create_langchain_tools(tool_nodes))
                for r_node in rag_nodes:
                    worker_tools.append(self._create_rag_tool(r_node))

                # Instantiate the worker LLM
                model_name = agent_node.data.agentModel or "gpt-4o-mini"
                from models.graph import Node as GraphNode, NodeData as GraphNodeData
                dummy_node = GraphNode(
                    id=node_id,
                    type="llm",
                    position=agent_node.position,
                    data=GraphNodeData(
                        label=agent_name,
                        model=model_name,
                        systemPrompt=system_prompt
                    )
                )
                llm = self._get_llm(dummy_node, worker_tools)

                messages = []
                if system_prompt:
                    messages.append(SystemMessage(content=system_prompt))
                messages.append(HumanMessage(content=task))

                if worker_tools:
                    current_messages = list(messages)
                    for loop_idx in range(5):
                        resp_msg = llm.invoke(current_messages)
                        current_messages.append(resp_msg)
                        if hasattr(resp_msg, "tool_calls") and resp_msg.tool_calls:
                            for tc in resp_msg.tool_calls:
                                matching_tool = next((t for t in worker_tools if t.name == tc["name"]), None)
                                if matching_tool:
                                    if self.logger:
                                        self.logger.info(f"Worker tool execution: {tc['name']}", {
                                            "node_id": node_id,
                                            "tool": tc['name']
                                        })
                                    tool_output = matching_tool.invoke(tc["args"])
                                    current_messages.append(ToolMessage(
                                        content=str(tool_output),
                                        tool_call_id=tc["id"]
                                    ))
                                else:
                                    current_messages.append(ToolMessage(
                                        content=f"Error: Tool {tc['name']} not found.",
                                        tool_call_id=tc["id"]
                                    ))
                        else:
                            response_text = resp_msg.content
                            break
                    else:
                        response_text = current_messages[-1].content
                else:
                    response_text = llm.invoke(messages).content

                if self.logger:
                    self.logger.success(f"Worker agent completed: {response_text[:100]}...", {
                        "node_id": node_id,
                        "status": "success"
                    })
                return response_text

            except Exception as e:
                error_msg = f"Worker agent execution failed: {str(e)}"
                if self.logger:
                    self.logger.error(error_msg, {
                        "node_id": node_id,
                        "status": "error"
                    })
                return error_msg

        return StructuredTool(
            name=clean_name,
            description=description,
            func=agent_fn,
            args_schema=AgentInput
        )

    def _get_llm(self, node: Node, tools: List[BaseTool]):
        """Get or create LLM instance with tools bound"""
        model_name = node.data.model or "gpt-4o-mini"

        # Route based on model string
        if model_name.startswith("gpt"):
            api_key = os.getenv("OPENAI_API_KEY", "dummy-key-for-testing")
            llm = ChatOpenAI(
                model=model_name,
                temperature=0.7,
                openai_api_key=api_key
            )
        else:
            api_key = os.getenv("NVIDIA_API_KEY", "")
            llm = ChatNVIDIA(
                model=model_name,
                temperature=0.7,
                nvidia_api_key=api_key
            )

        # Bind tools to LLM
        if tools:
            llm = llm.bind_tools(tools)
            if self.logger:
                self.logger.info(f"Bound {len(tools)} tools to LLM", {"model": model_name})

        return llm

    def _is_mock_mode(self) -> bool:
        """Check if we're in mock mode"""
        openai_key = os.getenv("OPENAI_API_KEY", "")
        nvidia_key = os.getenv("NVIDIA_API_KEY", "")
        has_openai = openai_key and not openai_key.startswith("dummy") and openai_key != "test"
        has_nvidia = nvidia_key and not nvidia_key.startswith("dummy") and nvidia_key != "test"
        return not (has_openai or has_nvidia)

    def _generate_mock_response(self, user_input: str, system_prompt: str) -> str:
        """Generate realistic mock response"""
        has_cyrillic = any(ord(char) >= 0x0400 and ord(char) <= 0x04FF for char in user_input)

        if has_cyrillic:
            if any(word in user_input.lower() for word in ["вернуть", "повернути", "возврат"]):
                return """Для возврата товара выполните следующие шаги:

1. Обратитесь в службу поддержки в течение 14 дней с момента покупки
2. Предоставьте чек или номер заказа
3. Товар должен быть в оригинальной упаковке
4. Возврат средств происходит в течение 5-7 рабочих дней

📧 Email: support@company.com
📞 Телефон: 8-800-123-45-67"""
            else:
                return f"""Спасибо за ваш вопрос: "{user_input}"

Я - тестовый помощник (MOCK режим). Для получения реальных ответов от AI необходимо:
1. Добавить OPENAI_API_KEY в файл backend/.env
2. Перезапустить backend"""
        else:
            if any(word in user_input.lower() for word in ["return", "refund"]):
                return """To return a product:

1. Contact support within 14 days
2. Provide receipt or order number
3. Product must be in original packaging
4. Refund processed within 5-7 business days

📧 Email: support@company.com"""
            else:
                return f"""Thank you for your question: "{user_input}"

I'm a test assistant (MOCK mode). To get real AI responses:
1. Add OPENAI_API_KEY to backend/.env file
2. Restart the backend"""

    def _should_continue(self, state: AgentState) -> str:
        """Decide whether to continue to tools or end"""
        messages = state["messages"]
        last_message = messages[-1]

        # If the last message has tool calls, route to tools
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            if self.logger:
                self.logger.info(f"Agent calling {len(last_message.tool_calls)} tool(s)", {
                    "tools": [tc["name"] for tc in last_message.tool_calls]
                })
            return "tools"

        # Otherwise, end the loop
        if self.logger:
            self.logger.success("Agent reasoning complete, proceeding to action", {})
        return "end"

    def _call_model(self, state: AgentState, llm_node: Node, llm_with_tools) -> AgentState:
        """Call the LLM model (hub node)"""
        messages = state["messages"]

        if self.logger:
            self.logger.info(f"LLM processing (iteration {len([m for m in messages if isinstance(m, AIMessage)]) + 1})", {
                "node_id": llm_node.id,
                "model": llm_node.data.model,
                "status": "running"
            })

        # Check mock mode
        if self._is_mock_mode():
            user_input = state.get("input", "")
            system_prompt = llm_node.data.systemPrompt or "You are a helpful assistant."
            mock_response = self._generate_mock_response(user_input, system_prompt)

            response_message = AIMessage(content=mock_response)
            if self.logger:
                self.logger.success(f"LLM response (mock): {mock_response[:100]}...", {
                    "node_id": llm_node.id,
                    "status": "success"
                })

            return {"messages": [response_message]}

        # Real LLM call
        response = llm_with_tools.invoke(messages)

        if self.logger:
            content_preview = response.content[:100] if response.content else "[tool calls]"
            self.logger.success(f"LLM response: {content_preview}...", {"node_id": llm_node.id})

        return {"messages": [response]}

    def _execute_action(self, state: AgentState, action_node: Node) -> AgentState:
        """Execute the action node"""
        # Extract final output from messages first (needed regardless of action node)
        messages = state["messages"]
        final_message = None

        # Find the last AI message that has content and NO tool calls
        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                # Skip messages that only contain tool calls
                has_tool_calls = hasattr(msg, "tool_calls") and msg.tool_calls
                if msg.content and not has_tool_calls:
                    final_message = msg.content
                    break
                # If message has both content and tool calls, take only the content
                elif msg.content and has_tool_calls:
                    final_message = msg.content
                    break

        output_message = final_message or state.get("output", "No output")

        # Clean up output: remove any JSON-like tool call artifacts
        # Some models incorrectly output tool calls as text instead of using proper tool calling
        import re
        # Remove patterns like: {"name": "tool_name", "parameters": {...}}
        output_message = re.sub(r'\{["\']name["\']\s*:\s*["\'][^"\']+["\']\s*,\s*["\']parameters["\']\s*:\s*\{[^}]*\}\}', '', output_message)
        # Remove patterns like: {"name": "tool_name", "arguments": {...}}
        output_message = re.sub(r'\{["\']name["\']\s*:\s*["\'][^"\']+["\']\s*,\s*["\']arguments["\']\s*:\s*\{[^}]*\}\}', '', output_message)
        # Clean up extra whitespace
        output_message = output_message.strip()

        # If no action node, just set the output and return
        if not action_node:
            if self.logger:
                self.logger.warning("No action node found, skipping action execution", {})
            state["output"] = output_message
            return state

        action_type = action_node.data.actionType
        if self.logger:
            self.logger.info(f"Executing action: {action_type}", {
                "node_id": action_node.id,
                "status": "running"
            })

        if action_type == "http_post":
            endpoint_url = action_node.data.config or ""
            if not endpoint_url:
                error_msg = "HTTP POST action requires endpoint URL"
                if self.logger:
                    self.logger.error(error_msg, {
                        "node_id": action_node.id,
                        "status": "error"
                    })
                state["output"] = error_msg
            else:
                try:
                    payload = {"message": output_message}
                    response = requests.post(
                        endpoint_url,
                        json=payload,
                        headers={"Content-Type": "application/json"},
                        timeout=10
                    )
                    result_msg = f"HTTP POST sent to {endpoint_url}. Status: {response.status_code}"
                    state["output"] = output_message
                    if self.logger:
                        self.logger.success(f"HTTP POST successful: {response.status_code}", {
                            "node_id": action_node.id,
                            "url": endpoint_url,
                            "status": "success"
                        })
                except Exception as e:
                    error_msg = f"HTTP POST failed: {str(e)}"
                    if self.logger:
                        self.logger.error(error_msg, {
                            "node_id": action_node.id,
                            "status": "error"
                        })
                    state["output"] = output_message
        else:
            state["output"] = output_message
            if self.logger:
                self.logger.success(f"Action completed: {action_type}", {
                    "node_id": action_node.id,
                    "status": "success"
                })

        return state

    def compile(self) -> StateGraph:
        """Compile the Hub-and-Spoke graph into a LangGraph StateGraph with ReAct loop"""

        # Find the hub (LLM node)
        llm_node = self._find_llm_node()
        if self.logger:
            self.logger.info(f"Found LLM hub: {llm_node.data.label}", {"node_id": llm_node.id})

        # Find spokes (tool nodes and RAG nodes)
        tool_nodes = self._find_tool_nodes_for_llm(llm_node.id)
        rag_nodes = self._find_rag_nodes_for_llm(llm_node.id)
        agent_nodes = self._find_agent_nodes_for_llm(llm_node.id)
        hitl_node = self._find_hitl_node()

        if self.logger:
            self.logger.info(f"Found {len(tool_nodes)} tool spokes, {len(rag_nodes)} RAG spokes, {len(agent_nodes)} worker agent spokes, and {'1' if hitl_node else '0'} HITL nodes", {
                "tools": [t.data.toolType for t in tool_nodes],
                "rag_nodes": [r.data.ragName or "Knowledge Base" for r in rag_nodes],
                "agent_nodes": [a.data.label for a in agent_nodes]
            })

        # Find trigger and action
        trigger_node = self._find_trigger_node()
        action_node = self._find_action_node()

        # Create LangChain tools from tool nodes
        langchain_tools = self._create_langchain_tools(tool_nodes)

        # Create LangChain tools from RAG nodes
        for rag_node in rag_nodes:
            rag_tool = self._create_rag_tool(rag_node)
            langchain_tools.append(rag_tool)
            if self.logger:
                self.logger.info(f"Registered RAG tool: {rag_tool.name}", {"node_id": rag_node.id})

        # Create LangChain tools from Agent nodes
        for agent_node in agent_nodes:
            agent_tool = self._create_agent_tool(agent_node)
            langchain_tools.append(agent_tool)
            if self.logger:
                self.logger.info(f"Registered Agent tool: {agent_tool.name}", {"node_id": agent_node.id})

        # Create LLM with tools bound
        llm_with_tools = self._get_llm(llm_node, langchain_tools)

        # Build the StateGraph
        workflow = StateGraph(AgentState)

        # Add agent node (LLM hub)
        def agent_node(state: AgentState) -> AgentState:
            return self._call_model(state, llm_node, llm_with_tools)

        workflow.add_node("agent", agent_node)

        # Add tool node if tools exist
        if langchain_tools:
            tool_node = ToolNode(langchain_tools)

            # Wrap tool node to add logging
            def logged_tool_node(state: AgentState) -> AgentState:
                # Build lookup map of tool name to node ID for logging
                tool_name_to_node_id = {}
                for t in tool_nodes:
                    tool_name_to_node_id[t.data.toolType] = t.id
                for r in rag_nodes:
                    clean_name = f"search_knowledge_base_{r.id.replace('-', '_')}"
                    tool_name_to_node_id[clean_name] = r.id
                for a in agent_nodes:
                    clean_name = f"call_agent_{a.id.replace('-', '_')}"
                    tool_name_to_node_id[clean_name] = a.id

                if self.logger:
                    messages = state["messages"]
                    last_message = messages[-1]
                    if hasattr(last_message, "tool_calls"):
                        for tool_call in last_message.tool_calls:
                            tool_node_id = tool_name_to_node_id.get(tool_call['name'])

                            self.logger.info(f"Executing tool: {tool_call['name']}", {
                                "node_id": tool_node_id,
                                "args": tool_call.get("args", {}),
                                "status": "running"
                            })

                result = tool_node.invoke(state)

                if self.logger:
                    messages = state["messages"]
                    last_message = messages[-1]
                    if hasattr(last_message, "tool_calls"):
                        for tool_call in last_message.tool_calls:
                            tool_node_id = tool_name_to_node_id.get(tool_call['name'])

                            # Find the tool message content
                            tool_output = "Tool executed successfully"
                            for tm in reversed(result["messages"]):
                                if isinstance(tm, ToolMessage) and tm.tool_call_id == tool_call.get("id"):
                                    tool_output = tm.content
                                    break

                            self.logger.success(f"Tool completed: {tool_call['name']}", {
                                "node_id": tool_node_id,
                                "status": "success",
                                "output": tool_output[:100]
                            })

                return result

            workflow.add_node("tools", logged_tool_node)

        # Add action node
        def action_node_func(state: AgentState) -> AgentState:
            return self._execute_action(state, action_node)

        workflow.add_node("action", action_node_func)

        # Set entry point
        workflow.set_entry_point("agent")

        # Next step after LLM processing (either HITL node or Action node)
        next_step = "hitl" if hitl_node else "action"

        # Add conditional edges for ReAct loop
        if langchain_tools:
            workflow.add_conditional_edges(
                "agent",
                self._should_continue,
                {
                    "tools": "tools",
                    "end": next_step
                }
            )
            # Tools always loop back to agent
            workflow.add_edge("tools", "agent")
        else:
            # No tools, go directly to action/hitl
            workflow.add_edge("agent", next_step)

        # Add hitl node function if it exists
        if hitl_node:
            def hitl_node_func(state: AgentState) -> AgentState:
                if self.logger:
                    self.logger.success("Human approval received. Resuming execution...", {
                        "node_id": hitl_node.id,
                        "status": "success"
                    })
                return state

            workflow.add_node("hitl", hitl_node_func)
            workflow.add_edge("hitl", "action")

        # Action is terminal
        workflow.add_edge("action", END)

        if self.logger:
            self.logger.success("Agentic graph compiled successfully", {
                "architecture": "Hub-and-Spoke",
                "tools_count": len(langchain_tools)
            })

        if hitl_node:
            return workflow.compile(checkpointer=self.checkpointer, interrupt_before=["hitl"])
        else:
            return workflow.compile(checkpointer=self.checkpointer)

    def create_initial_state(self, user_input: str, llm_node: Node) -> AgentState:
        """Create initial state for graph execution

        Note: When using checkpointer with thread_id, only the new user message
        should be added. The checkpointer automatically maintains conversation history.
        The system prompt is only added on the first message of a thread.
        """
        # Only add the new user message
        # The checkpointer will merge this with existing conversation history
        messages = [
            HumanMessage(content=user_input)
        ]

        return {
            "messages": messages,
            "input": user_input,
            "output": "",
            "current_node": ""
        }
