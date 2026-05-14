from langgraph.graph import StateGraph, START, END

from agent.state import AgentState
from agent.nodes import agent_node, tool_executor_node
from agent.router import route_after_agent

# ── Graph assembly ────────────────────────────────────────────────────────────────────────────
#
# Visual layout of what we're building:
#
#   START
#     │
#     ▼
#   agent_node ──(tool_calls?)──► tool_executor_node ──► agent_node  (loop)
#              └──(no calls)───► END
#
# Two nodes.  One conditional edge.  One fixed back-edge.  That's it.

graph = StateGraph(AgentState)

# Register nodes
graph.add_node("agent", agent_node)
graph.add_node("tool_executor", tool_executor_node)

# Entry point
graph.add_edge(START, "agent")

# Conditional edge after agent_node — the router decides where to go
graph.add_conditional_edges(
    "agent",
    route_after_agent,
    {
        "call_tools": "tool_executor",  # Claude wants to call a tool
        "end": END,                     # Claude is done
    },
)

# tool_executor always loops back to agent so Claude can see the results
graph.add_edge("tool_executor", "agent")

# Compile into a runnable object — this validates the graph structure
compiled_graph = graph.compile()
