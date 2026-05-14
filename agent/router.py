from langchain_core.messages import AIMessage
from agent.state import AgentState


def route_after_agent(state: AgentState) -> str:
    """
    The single conditional router in the graph.

    Called after every agent_node execution to decide the next node:
      - "call_tools"  if Claude emitted tool_calls (wants to use a tool)
      - "end"         if Claude emitted a plain message (reasoning is complete)

    This is the ONLY branching point in the entire graph — everything else is
    a fixed edge.  Inspecting tool_calls on the last AIMessage is the canonical
    LangGraph pattern for detecting agent termination.
    """
    last_message: AIMessage = state["messages"][-1]

    if last_message.tool_calls:
        print(f"\n  [router] tool_calls detected → routing to tool_executor_node")
        return "call_tools"

    print(f"\n  [router] no tool_calls → routing to END")
    return "end"
