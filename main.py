"""
Cloud Infrastructure Advisory Agent — entry point.

Run with:
    uv run python main.py

The agent uses a ReAct loop (Reason → Act → Observe) implemented in LangGraph.
Every step of the loop is printed to the console so you can follow the agent's
decision-making in real time.
"""

# load_dotenv() MUST be called before importing agent modules because agent/nodes.py
# instantiates the ChatAnthropic model at module level and reads ANTHROPIC_API_KEY.
from dotenv import load_dotenv
load_dotenv()

import os
import sys
from langchain_core.messages import HumanMessage, AIMessage

from agent.graph import compiled_graph

# ── Constants ─────────────────────────────────────────────────────────────────────────────────
_BANNER = """
============================================================
  Cloud Infrastructure Advisory Agent
  Powered by Claude ({model})
  Framework: LangGraph ReAct loop
============================================================
  Ask any Cloud / DevOps infrastructure question.
  The agent will autonomously research and compose
  a structured advisory report.

  Type 'exit' or press Ctrl+C to quit.
============================================================
"""

_SECTION = "=" * 60


def _print_final_answer(state: dict) -> None:
    """Extract and print the last AIMessage from the completed graph state."""
    messages = state["messages"]
    iterations = state["iteration_count"]

    # Walk backwards to find the last AIMessage (the agent's closing response)
    final_message = next(
        (m for m in reversed(messages) if isinstance(m, AIMessage)),
        None,
    )

    print(f"\n{_SECTION}")
    print("  AGENT RESPONSE")
    print(_SECTION)

    if final_message and final_message.content:
        print(final_message.content)
    else:
        # Fallback: the last ToolMessage holds the formatted report
        last_tool = next(
            (m for m in reversed(messages) if hasattr(m, "content") and not isinstance(m, (HumanMessage, AIMessage))),
            None,
        )
        if last_tool:
            print(last_tool.content)
        else:
            print("(no content in final message)")

    print(f"\n{_SECTION}")
    print(f"  Completed in {iterations} iteration(s)  |  MAX_ITERATIONS = 6")
    print(_SECTION)


def run_agent(question: str) -> None:
    """Build initial state and invoke the compiled LangGraph graph."""
    initial_state = {
        "messages": [HumanMessage(content=question)],
        "iteration_count": 0,
    }

    print(f"\n{_SECTION}")
    print("  AGENT STARTING")
    print(_SECTION)
    print(f"  Question: {question}")
    print(f"{_SECTION}")

    try:
        final_state = compiled_graph.invoke(initial_state)
        _print_final_answer(final_state)

    except RuntimeError as exc:
        print(f"\n[ERROR] {exc}")
        print("Hint: reduce complexity of your question or increase MAX_ITERATIONS in agent/state.py")

    except (TypeError, ValueError) as exc:
        msg = str(exc)
        if "api_key" in msg or "authentication" in msg.lower() or "Authorization" in msg:
            print("\n[AUTH ERROR] ANTHROPIC_API_KEY is missing or invalid.")
            print("  1. Copy .env.example to .env")
            print("  2. Set ANTHROPIC_API_KEY=sk-ant-... in .env")
            print("  3. Run again: uv run python main.py")
        else:
            print(f"\n[ERROR] {type(exc).__name__}: {exc}")
            raise

    except Exception as exc:
        print(f"\n[UNEXPECTED ERROR] {type(exc).__name__}: {exc}")
        raise


def main() -> None:
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("\n[ERROR] ANTHROPIC_API_KEY is not set.")
        print("  1. Copy .env.example to .env")
        print("  2. Set ANTHROPIC_API_KEY=sk-ant-... in .env")
        print("  3. Run again: uv run python main.py\n")
        sys.exit(1)

    model_name = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001")
    print(_BANNER.format(model=model_name))

    # Support single-shot CLI mode: uv run python main.py "your question here"
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:]).strip()
        if question:
            run_agent(question)
            return

    # Interactive loop mode
    while True:
        try:
            question = input("\nUser: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nGoodbye!")
            break

        if not question:
            continue

        if question.lower() in {"exit", "quit", "q", "bye"}:
            print("Goodbye!")
            break

        run_agent(question)


if __name__ == "__main__":
    main()
