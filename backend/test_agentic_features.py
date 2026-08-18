"""
Agentic Features Integration Test Script
Tests: Specialist agent nodes, HITL interrupts, checkpointer state, and resumption.
"""
import sys
import os
import json

# Ensure we can import from the backend directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.graph import Node, NodeData, Edge, GraphSchema, Position
from routers.langgraph_compiler_agentic import AgenticLangGraphCompiler
from langgraph.checkpoint.memory import MemorySaver

def test_compiler_compilation():
    print("=" * 60)
    print("TEST 1: Schema Compilation with Specialist Agent & HITL")
    print("=" * 60)

    # 1. Define nodes
    trigger_node = Node(
        id="trigger-1",
        type="trigger",
        position=Position(x=100, y=100),
        data=NodeData(label="Trigger", triggerType="manual")
    )
    
    llm_node = Node(
        id="llm-1",
        type="llm",
        position=Position(x=300, y=100),
        data=NodeData(
            label="Supervisor",
            model="gpt-4o-mini",
            systemPrompt="You are a supervisor. If the user asks for a sales report, call the sales_specialist agent tool. Otherwise answer directly."
        )
    )

    agent_node = Node(
        id="agent-1",
        type="agent",
        position=Position(x=100, y=300),
        data=NodeData(
            label="Sales Specialist",
            agentModel="gpt-4o-mini",
            agentRole="sales_specialist",
            agentSystemPrompt="You are a sales specialist. Output the text: 'The sales report for Q1 shows a 25% growth.'"
        )
    )

    hitl_node = Node(
        id="hitl-1",
        type="hitl",
        position=Position(x=500, y=100),
        data=NodeData(
            label="Approval Gate",
            hitlMessage="Do you approve sending this report?",
            hitlTimeout=30
        )
    )

    action_node = Node(
        id="action-1",
        type="action",
        position=Position(x=700, y=100),
        data=NodeData(label="Log Output", actionType="log")
    )

    # 2. Define edges (Hub and Spoke)
    edges = [
        # Trigger to LLM
        Edge(id="e1", source="trigger-1", target="llm-1", targetHandle="execution_in"),
        # Agent worker to LLM tool list
        Edge(id="e2", source="agent-1", target="llm-1", targetHandle="tools_in"),
        # LLM execution to HITL
        Edge(id="e3", source="llm-1", sourceHandle="execution_out", target="hitl-1", targetHandle="execution_in"),
        # HITL to final Action
        Edge(id="e4", source="hitl-1", sourceHandle="execution_out", target="action-1", targetHandle="execution_in")
    ]

    schema = GraphSchema(
        nodes=[trigger_node, llm_node, agent_node, hitl_node, action_node],
        edges=edges
    )

    # Compile the graph
    checkpointer = MemorySaver()
    compiler = AgenticLangGraphCompiler(
        schema,
        checkpointer=checkpointer
    )
    compiled_graph = compiler.compile()

    print("  [OK] Compiled successfully")
    assert compiled_graph is not None, "Compiled graph should not be None"
    
    # Verify the compiled graph structure has the correct nodes
    print(f"  Graph Nodes: {list(compiled_graph.nodes.keys())}")
    assert "agent" in compiled_graph.nodes, "Supervisor node 'agent' should be compiled"
    assert "hitl" in compiled_graph.nodes, "HITL node 'hitl' should be compiled"
    assert "action" in compiled_graph.nodes, "Action node 'action' should be compiled"
    
    print("  [PASS]\n")
    return compiled_graph, compiler, schema


def test_hitl_interruption_and_resume(compiled_graph, compiler):
    print("=" * 60)
    print("TEST 2: HITL Interruption & State Resumption")
    print("=" * 60)

    # Create thread config
    thread_id = "test-thread-hitl-001"
    config = {"configurable": {"thread_id": thread_id}}

    # Initial input targeting LLM
    initial_input = "Generate the sales report and log it"
    state_input = {
        "input": initial_input,
        "messages": [],
        "output": ""
    }

    print(f"  [1] Starting graph run for thread '{thread_id}' with input: '{initial_input}'")
    
    # We invoke it. Since there is a HITL node, it should pause before hitl execution
    # and wait for checkpointer to be resumed.
    result = compiled_graph.invoke(state_input, config=config)
    
    # Let's inspect the graph state
    graph_state = compiled_graph.get_state(config)
    print(f"  Current next nodes in queue: {graph_state.next}")
    
    # Verify that the graph state is paused right before the HITL node!
    assert "hitl" in graph_state.next, "Expected execution to halt before 'hitl' node"
    print("  [OK] Halting at HITL node verified")

    # Let's inspect the message history stored in state to ensure agent tool was called
    messages = graph_state.values.get("messages", [])
    print(f"  Total messages in state: {len(messages)}")
    for i, msg in enumerate(messages):
        print(f"    msg {i+1} ({msg.type}): {msg.content[:80]}...")

    # Now let's resume execution: simulating 'approved = True'
    print("\n  [2] Simulating human approval and resuming execution...")
    
    # Resume the graph by passing None as state updates or updating with approval details
    resume_result = compiled_graph.invoke(None, config=config)
    
    # Check updated state
    updated_state = compiled_graph.get_state(config)
    print(f"  New next nodes: {updated_state.next}")
    assert len(updated_state.next) == 0, "Expected execution to complete after resuming and approving"
    
    print(f"  Final execution output: '{resume_result.get('output')}'")
    assert len(resume_result.get("output", "")) > 0, "Expected output after graph completion"
    print("  [OK] Graph execution completed after resume verified")
    print("  [PASS]\n")


if __name__ == "__main__":
    print("\n[Test] Agentic Features (Multi-Agent & HITL) Test Suite\n")

    try:
        compiled_graph, compiler, schema = test_compiler_compilation()
        
        # Ensure we have OpenAI/OpenRouter API key or run in mock mode
        if not os.environ.get("OPENAI_API_KEY") and not os.environ.get("NVIDIA_API_KEY"):
            print("  [Warning] No API keys found in environment. Mocking API responses is required or the test will run with mock LLM outputs.")
            # We can still run the test, compiler will use fallback or fail gracefully
            
        test_hitl_interruption_and_resume(compiled_graph, compiler)

        print("=" * 60)
        print("ALL AGENTIC FEATURE TESTS PASSED!")
        print("=" * 60)

    except Exception as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
