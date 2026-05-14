# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

A minimal LangGraph + Claude agent built as a learning demo for Cloud/DevOps engineers. It answers infrastructure questions (e.g. S3 security, IAM best practices) by autonomously calling tools and composing a structured advisory report. Every design choice prioritises explainability over production features. Full design rationale lives in [SPEC.md](SPEC.md).

## Setup and Run

```bash
# Copy and fill in your Anthropic API key
cp .env.example .env
# Edit .env: set ANTHROPIC_API_KEY=sk-ant-...

# Run — uv installs deps automatically on first run
uv run python main.py

# Single-shot mode (no interactive prompt)
uv run python main.py "What are the best practices for securing an S3 bucket?"

# Override the Claude model (default: claude-haiku-4-5-20251001)
CLAUDE_MODEL=claude-sonnet-4-6 uv run python main.py
```

Dependencies are declared in [pyproject.toml](pyproject.toml). No manual `pip install` needed — `uv run` handles the virtualenv.

## Architecture

Two-node LangGraph `StateGraph` implementing the ReAct (Reason → Act → Observe) loop:

```
START → agent_node ──(tool_calls present?)──► tool_executor_node ──► agent_node  (loop)
                   └──(no tool_calls)──────► END
```

**`agent_node`** ([agent/nodes.py](agent/nodes.py)) — calls Claude with the full message history. Claude either emits `tool_calls` in its `AIMessage` (go to tool executor) or a plain `AIMessage` (done). Enforces `MAX_ITERATIONS = 6`; raises `RuntimeError` deliberately so learners see the guard fire.

**`tool_executor_node`** ([agent/nodes.py](agent/nodes.py)) — reads `tool_calls` from the last `AIMessage`, dispatches to Python functions by name via `_TOOL_REGISTRY`, wraps each result in a `ToolMessage`. Always routes back to `agent_node`.

**Router** ([agent/router.py](agent/router.py)) — the single conditional edge. Returns `"call_tools"` if the last `AIMessage.tool_calls` is non-empty, else `"end"`. Only branching point in the graph.

**State** ([agent/state.py](agent/state.py)) — `AgentState` TypedDict:
- `messages: Annotated[list[AnyMessage], add_messages]` — the `add_messages` reducer appends on every turn; never overwrites. Holds the full `HumanMessage → AIMessage → ToolMessage → …` chain.
- `iteration_count: int` — replaced each turn (no reducer); used by the MAX_ITERATIONS guard.

**Tools** ([agent/tools.py](agent/tools.py)) — three `@tool`-decorated functions Claude can call:
- `search_best_practices(topic, category)` — looks up from `data/knowledge_base.py` BEST_PRACTICES dict
- `check_compliance_rules(service, rule_type)` — same dict, COMPLIANCE_RULES branch; `rule_type` in `{cis, well_architected, nist}`
- `format_report(question, best_practices, compliance_rules)` — pure string formatting; no LLM call; makes Claude's synthesis step explicit

**Knowledge base** ([data/knowledge_base.py](data/knowledge_base.py)) — two plain Python dicts covering S3, IAM, VPC, EC2, RDS, Lambda, Terraform state, Kubernetes. No network calls; deterministic offline output.

**Graph assembly** ([agent/graph.py](agent/graph.py)) — all `add_node` / `add_edge` / `add_conditional_edges` calls; exports `compiled_graph`.

**Entry point** ([main.py](main.py)) — calls `load_dotenv()` before any agent import (critical: the model is instantiated at module load time). Runs the `User:` interactive loop or accepts a CLI argument for single-shot mode.

## Key Constraints

- **`load_dotenv()` must precede agent imports in main.py** — `ChatAnthropic` is created at module level in `nodes.py` and reads `ANTHROPIC_API_KEY` immediately on import.
- **`MAX_ITERATIONS` raises loudly** — do not convert to a silent early exit; the visible error is intentional for learners.
- **In-memory knowledge base only** — no network calls inside tools; offline reproducibility is intentional.
- **No LangChain agent executors** — the graph is hand-assembled (not `create_react_agent`) so every wire is explicit and readable.
- **Verbose console output** — keep the `print` statements in nodes and router; they are the primary learning mechanism.
- **Model via env var only** — never hardcode a model string outside the default in `nodes.py`.
