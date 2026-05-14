import os
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, ToolMessage

from agent.state import AgentState, MAX_ITERATIONS
from agent.tools import search_best_practices, check_compliance_rules, format_report

# ── Model setup (module-level: created once, reused across all invocations) ──────────────────
# .bind_tools() attaches the tool schemas so Claude knows what tools are available
# and can emit tool_calls inside its AIMessage responses.
_TOOLS = [search_best_practices, check_compliance_rules, format_report]
_TOOL_REGISTRY: dict[str, object] = {t.name: t for t in _TOOLS}

_model = ChatAnthropic(
    model=os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001"),
).bind_tools(_TOOLS)

# ── Formatting helpers ────────────────────────────────────────────────────────────────────────

_DIVIDER = "─" * 60


def _fmt_args(args: dict) -> str:
    return ", ".join(f"{k}={v!r}" for k, v in args.items())


# ── Nodes ─────────────────────────────────────────────────────────────────────────────────────

def agent_node(state: AgentState) -> dict:
    """
    The 'brain' node.

    Receives the full message history and asks Claude what to do next.
    Claude either:
      (a) emits an AIMessage with tool_calls  → the router sends us to tool_executor_node
      (b) emits a plain AIMessage (no calls)  → the router sends us to END
    """
    count = state["iteration_count"] + 1

    if count > MAX_ITERATIONS:
        raise RuntimeError(
            f"\n[agent_node] MAX_ITERATIONS ({MAX_ITERATIONS}) exceeded. "
            "The agent is stuck in a loop. Check your tools and system prompt."
        )

    msg_count = len(state["messages"])
    print(f"\n{_DIVIDER}")
    print(f"  ITERATION {count}  |  agent_node  |  {msg_count} message(s) in state")
    print(_DIVIDER)
    print("  Claude is reasoning...")

    response: AIMessage = _model.invoke(state["messages"])

    if response.tool_calls:
        for tc in response.tool_calls:
            print(f"\n  TOOL CALL  →  {tc['name']}")
            for k, v in tc["args"].items():
                # Truncate long values so the log stays readable
                display = repr(v)
                if len(display) > 120:
                    display = display[:117] + "..."
                print(f"    {k:20s} = {display}")
    else:
        print("\n  No tool call — Claude has finished reasoning.")

    return {
        "messages": [response],
        "iteration_count": count,
    }


def tool_executor_node(state: AgentState) -> dict:
    """
    The 'hands' node.

    Reads every tool_call from the latest AIMessage, dispatches to the matching
    Python function, and wraps each result in a ToolMessage.  Always routes back
    to agent_node so Claude can see the results.
    """
    last_ai_message: AIMessage = state["messages"][-1]
    tool_messages: list[ToolMessage] = []

    print(f"\n{_DIVIDER}")
    print(f"  tool_executor_node  |  executing {len(last_ai_message.tool_calls)} tool(s)")
    print(_DIVIDER)

    for tool_call in last_ai_message.tool_calls:
        name = tool_call["name"]
        args = tool_call["args"]
        tool_fn = _TOOL_REGISTRY[name]

        print(f"\n  Running: {name}({_fmt_args(args)})")

        result = tool_fn.invoke(args)
        result_str = str(result)

        print(f"  Result : {len(result_str)} chars returned")
        # Print a short preview so learners can see what came back
        preview = result_str[:200].replace("\n", " ")
        if len(result_str) > 200:
            preview += " ..."
        print(f"  Preview: {preview}")

        tool_messages.append(
            ToolMessage(
                content=result_str,
                tool_call_id=tool_call["id"],
            )
        )

    return {"messages": tool_messages}
