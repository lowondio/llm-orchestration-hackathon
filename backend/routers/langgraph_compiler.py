from typing import Dict, Any, List, Optional, TypedDict
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.messages import HumanMessage, SystemMessage
from models.graph import GraphSchema, Node
from tools import web_search, calculator
import os
import requests

class AgentState(TypedDict):
    """State object for LangGraph execution"""
    input: str
    output: str
    current_node: str
    tool_result: str

class LangGraphCompiler:
    def __init__(self, graph_schema: GraphSchema, logger=None):
        self.graph_schema = graph_schema
        self.nodes_map = {node.id: node for node in graph_schema.nodes}
        self.edges_map = self._build_edges_map()
        self.llm_instances: Dict[str, ChatOpenAI] = {}
        self.logger = logger  # ExecutionLogger instance

    def _build_edges_map(self) -> Dict[str, List[str]]:
        """Build adjacency list from edges"""
        edges_map = {}
        for edge in self.graph_schema.edges:
            if edge.source not in edges_map:
                edges_map[edge.source] = []
            edges_map[edge.source].append(edge.target)
        return edges_map

    def _get_llm(self, node: Node):
        """Get or create LLM instance for a node - supports OpenAI and Nvidia"""
        if node.id not in self.llm_instances:
            model_name = node.data.model or "gpt-4o-mini"

            # Route based on model string
            if model_name.startswith("gpt"):
                # OpenAI models
                api_key = os.getenv("OPENAI_API_KEY", "dummy-key-for-testing")
                self.llm_instances[node.id] = ChatOpenAI(
                    model=model_name,
                    temperature=0.7,
                    openai_api_key=api_key
                )
            else:
                # Nvidia models (meta/llama3-70b-instruct, mistralai/mixtral-8x7b-instruct-v0.1, etc.)
                api_key = os.getenv("NVIDIA_API_KEY", "")
                self.llm_instances[node.id] = ChatNVIDIA(
                    model=model_name,
                    temperature=0.7,
                    nvidia_api_key=api_key
                )

        return self.llm_instances[node.id]

    def _is_mock_mode(self) -> bool:
        """Check if we're in mock mode (no real API key)"""
        openai_key = os.getenv("OPENAI_API_KEY", "")
        nvidia_key = os.getenv("NVIDIA_API_KEY", "")

        # Mock mode if neither key is valid
        has_openai = openai_key and not openai_key.startswith("dummy") and openai_key != "test"
        has_nvidia = nvidia_key and not nvidia_key.startswith("dummy") and nvidia_key != "test"

        return not (has_openai or has_nvidia)

    def _generate_mock_response(self, user_input: str, system_prompt: str) -> str:
        """Generate realistic mock response based on input language and content"""

        # Detect language
        has_cyrillic = any(ord(char) >= 0x0400 and ord(char) <= 0x04FF for char in user_input)

        # Common FAQ patterns
        if has_cyrillic:
            # Russian/Ukrainian
            if any(word in user_input.lower() for word in ["вернуть", "повернути", "возврат"]):
                return """Для возврата товара выполните следующие шаги:

1. Обратитесь в службу поддержки в течение 14 дней с момента покупки
2. Предоставьте чек или номер заказа
3. Товар должен быть в оригинальной упаковке и без следов использования
4. Возврат средств происходит в течение 5-7 рабочих дней на ту же карту

Если у вас остались вопросы, свяжитесь с нами:
📧 Email: support@company.com
📞 Телефон: 8-800-123-45-67"""

            elif any(word in user_input.lower() for word in ["доставка", "доставку", "доставки"]):
                return """Информация о доставке:

🚚 Способы доставки:
- Курьерская доставка (1-3 дня) - 300₽
- Почта России (5-10 дней) - 200₽
- Самовывоз (бесплатно)

📦 Бесплатная доставка при заказе от 3000₽

Отследить заказ можно в личном кабинете или по номеру трекинга."""

            elif any(word in user_input.lower() for word in ["оплата", "оплатить", "платить"]):
                return """Доступные способы оплаты:

💳 Банковские карты (Visa, MasterCard, Мир)
💰 Наличные при получении
📱 Электронные кошельки (ЮMoney, QIWI)
🏦 Банковский перевод

Оплата безопасна и защищена SSL-сертификатом."""

            else:
                return f"""Спасибо за ваш вопрос: "{user_input}"

Я - тестовый помощник (MOCK режим). Для получения реальных ответов от AI необходимо:
1. Добавить OPENAI_API_KEY в файл backend/.env
2. Перезапустить backend

Подробная инструкция в файле SETUP_REAL_LLM.md"""

        else:
            # English
            if any(word in user_input.lower() for word in ["return", "refund"]):
                return """To return a product, please follow these steps:

1. Contact support within 14 days of purchase
2. Provide receipt or order number
3. Product must be in original packaging
4. Refund processed within 5-7 business days

Contact us:
📧 Email: support@company.com
📞 Phone: 1-800-123-4567"""

            elif any(word in user_input.lower() for word in ["shipping", "delivery"]):
                return """Shipping information:

🚚 Shipping methods:
- Express delivery (1-3 days) - $10
- Standard shipping (5-10 days) - $5
- Store pickup (free)

📦 Free shipping on orders over $50

Track your order in your account or using tracking number."""

            else:
                return f"""Thank you for your question: "{user_input}"

I'm a test assistant (MOCK mode). To get real AI responses:
1. Add OPENAI_API_KEY to backend/.env file
2. Restart the backend

See SETUP_REAL_LLM.md for detailed instructions."""

    def _create_node_function(self, node: Node):
        """Create a function for a specific node type"""

        if node.type == "trigger":
            def trigger_node(state: AgentState) -> AgentState:
                msg = f"[Trigger] {node.data.label}"
                print(msg)
                if self.logger:
                    self.logger.info(f"Trigger node started: {node.data.label}", {"node_id": node.id})
                if "input" not in state:
                    state["input"] = "Default trigger input"
                state["current_node"] = node.id
                return state
            return trigger_node

        elif node.type == "llm":
            def llm_node(state: AgentState) -> AgentState:
                msg = f"[LLM] {node.data.label}"
                print(msg)
                if self.logger:
                    self.logger.info(f"LLM node started: {node.data.label}", {"node_id": node.id, "model": node.data.model})

                system_prompt = node.data.systemPrompt or "You are a helpful assistant."
                user_input = state.get("input", "")

                # Check if we're in mock mode
                if self._is_mock_mode():
                    # Generate realistic mock response based on language
                    mock_response = self._generate_mock_response(user_input, system_prompt)
                    state["output"] = mock_response
                    state["current_node"] = node.id
                    print(f"[LLM Response - MOCK MODE] {mock_response}")
                    if self.logger:
                        self.logger.success(f"LLM response (mock): {mock_response[:100]}...", {"node_id": node.id})
                else:
                    # Real LLM call
                    if self.logger:
                        self.logger.info(f"Calling LLM API with model: {node.data.model}", {"node_id": node.id})
                    llm = self._get_llm(node)
                    messages = [
                        SystemMessage(content=system_prompt),
                        HumanMessage(content=user_input)
                    ]
                    response = llm.invoke(messages)
                    state["output"] = response.content
                    state["current_node"] = node.id
                    print(f"[LLM Response] {response.content[:100]}...")
                    if self.logger:
                        self.logger.success(f"LLM response received: {response.content[:100]}...", {"node_id": node.id})

                return state
            return llm_node

        elif node.type == "tool":
            def tool_node(state: AgentState) -> AgentState:
                msg = f"[Tool] {node.data.label}"
                print(msg)
                tool_type = node.data.toolType
                if self.logger:
                    self.logger.info(f"Tool node started: {node.data.label}", {"node_id": node.id, "tool_type": tool_type})

                if tool_type == "web_search":
                    query = state.get("output", state.get("input", ""))
                    if self.logger:
                        self.logger.info(f"Executing web search with query: {query[:50]}...", {"node_id": node.id})
                    result = web_search.invoke({"query": query})
                    state["tool_result"] = result
                    state["output"] = result
                    print(f"[Tool Result] {result[:100]}...")
                    if self.logger:
                        self.logger.success(f"Web search completed: {result[:100]}...", {"node_id": node.id})

                elif tool_type == "calculator":
                    expression = state.get("output", state.get("input", ""))
                    if self.logger:
                        self.logger.info(f"Executing calculator with expression: {expression}", {"node_id": node.id})
                    result = calculator.invoke({"expression": expression})
                    state["tool_result"] = result
                    state["output"] = result
                    print(f"[Tool Result] {result}")
                    if self.logger:
                        self.logger.success(f"Calculator result: {result}", {"node_id": node.id})

                else:
                    state["tool_result"] = f"Tool {tool_type} not implemented"
                    state["output"] = state["tool_result"]
                    if self.logger:
                        self.logger.warning(f"Tool {tool_type} not implemented", {"node_id": node.id})

                state["current_node"] = node.id
                return state
            return tool_node

        elif node.type == "action":
            def action_node(state: AgentState) -> AgentState:
                msg = f"[Action] {node.data.label}"
                print(msg)
                action_type = node.data.actionType
                if self.logger:
                    self.logger.info(f"Action node started: {node.data.label}", {"node_id": node.id, "action_type": action_type})

                if action_type == "http_post":
                    # Get endpoint URL from node config
                    endpoint_url = node.data.config or ""
                    output_message = state.get("output", "No output")

                    if not endpoint_url:
                        error_msg = "HTTP POST action requires endpoint URL in config"
                        state["action_result"] = error_msg
                        if self.logger:
                            self.logger.error(error_msg, {"node_id": node.id})
                    else:
                        try:
                            if self.logger:
                                self.logger.info(f"Sending HTTP POST to {endpoint_url}", {"node_id": node.id})

                            # Send POST request with LLM output
                            payload = {"message": output_message}
                            response = requests.post(
                                endpoint_url,
                                json=payload,
                                headers={"Content-Type": "application/json"},
                                timeout=10
                            )

                            result_msg = f"HTTP POST sent to {endpoint_url}. Status: {response.status_code}"
                            state["action_result"] = result_msg
                            print(f"[Action Result] {result_msg}")

                            if self.logger:
                                self.logger.success(
                                    f"HTTP POST successful: {response.status_code}",
                                    {"node_id": node.id, "url": endpoint_url, "status": response.status_code}
                                )

                        except Exception as e:
                            error_msg = f"HTTP POST failed: {str(e)}"
                            state["action_result"] = error_msg
                            print(f"[Action Error] {error_msg}")
                            if self.logger:
                                self.logger.error(error_msg, {"node_id": node.id, "url": endpoint_url})
                else:
                    # Default action (log only)
                    state["action_result"] = f"Action {action_type} executed"
                    if self.logger:
                        self.logger.success(f"Action {action_type} executed", {"node_id": node.id})

                state["current_node"] = node.id
                return state
            return action_node

        else:
            def default_node(state: AgentState) -> AgentState:
                msg = f"[Unknown] {node.data.label}"
                print(msg)
                if self.logger:
                    self.logger.warning(f"Unknown node type: {node.type}", {"node_id": node.id})
                state["current_node"] = node.id
                return state
            return default_node

    def _get_next_node(self, current_node_id: str) -> Optional[str]:
        """Get the next node ID based on edges"""
        if current_node_id in self.edges_map:
            next_nodes = self.edges_map[current_node_id]
            if next_nodes:
                return next_nodes[0]
        return None

    def compile(self) -> StateGraph:
        """Compile the graph schema into a LangGraph StateGraph"""
        workflow = StateGraph(AgentState)

        # Add all nodes
        for node in self.graph_schema.nodes:
            node_function = self._create_node_function(node)
            workflow.add_node(node.id, node_function)

        # Find entry point (trigger node)
        trigger_nodes = [n for n in self.graph_schema.nodes if n.type == "trigger"]
        if not trigger_nodes:
            raise ValueError("No trigger node found in graph")

        entry_node = trigger_nodes[0].id
        workflow.set_entry_point(entry_node)

        # Add edges
        for edge in self.graph_schema.edges:
            workflow.add_edge(edge.source, edge.target)

        # Add terminal edges (nodes with no outgoing edges)
        all_sources = {edge.source for edge in self.graph_schema.edges}
        all_targets = {edge.target for edge in self.graph_schema.edges}
        terminal_nodes = all_targets - all_sources

        for node_id in terminal_nodes:
            workflow.add_edge(node_id, END)

        return workflow.compile()
