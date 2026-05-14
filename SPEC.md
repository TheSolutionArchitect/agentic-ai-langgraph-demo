# Cloud Infrastructure Advisory Agent — Technical Specification

**Project:** `agentic-ai-langgraph-demo`
**Version:** v1.0
**Date:** 2026-05-13
**Status:** Design / Pre-implementation

---

## 1. Purpose and Learning Goals

This project builds the smallest possible agentic AI workflow that still demonstrates every core concept a learner needs to understand. The scenario is deliberately chosen to be familiar to Cloud and DevOps engineers: answering infrastructure questions by autonomously researching and composing a structured advisory report.

After studying this project a learner will be able to explain:

| Concept | What you will see it do |
|---------|------------------------|
| **Agent state** | A typed dictionary that flows through the graph, carrying messages and metadata |
| **Tool calling** | Claude decides *which* tool to call and *why*, then reads the result |
| **ReAct loop** | Reason → Act → Observe → Reason again, until Claude decides it is done |
| **LangGraph graph** | Nodes, directed edges, and the conditional router that drives the loop |
| **Termination condition** | How the agent knows when to stop and return a final answer |
| **Anthropic integration** | How to bind tools to a Claude model and stream responses through LangGraph |

---

## 2. Problem Statement

A Cloud or DevOps engineer types a natural-language question about infrastructure best practices — for example:

> "What are the best practices for securing an S3 bucket that stores sensitive customer data?"

The agent must autonomously:

1. Understand the question and plan its research steps.
2. Call tools to look up relevant best practices and compliance rules.
3. Synthesize everything it has learned into a structured advisory report.
4. Know when it has gathered enough information and stop without being told.

No human intervention happens between the question and the final report. That autonomous, multi-step, tool-driven loop is the definition of agentic AI.

---

## 3. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        LangGraph StateGraph                      │
│                                                                  │
│   ┌───────┐          ┌─────────────────┐      ┌──────────────┐  │
│   │ START │─────────►│   agent_node    │─────►│     END      │  │
│   └───────┘          │                 │      └──────────────┘  │
│                      │  Claude claude- │  (no tool call needed) │
│                      │  haiku-4-5 or  │                         │
│                      │  sonnet-4-6     │                         │
│                      └────────┬────────┘                         │
│                               │ tool_call                        │
│                               ▼                                  │
│                      ┌─────────────────┐                         │
│                      │ tool_executor_  │                         │
│                      │     node        │                         │
│                      │                 │                         │
│                      │ ┌─────────────┐ │                         │
│                      │ │search_best_ │ │                         │
│                      │ │ practices() │ │                         │
│                      │ ├─────────────┤ │                         │
│                      │ │check_compli-│ │                         │
│                      │ │  ance()     │ │                         │
│                      │ ├─────────────┤ │                         │
│                      │ │format_      │ │                         │
│                      │ │ report()    │ │                         │
│                      │ └─────────────┘ │                         │
│                      └────────┬────────┘                         │
│                               │ always loops back                │
│                               └──────────────────────────────────┘
│                                          ▲                       │
│                                (back to agent_node)              │
└─────────────────────────────────────────────────────────────────┘
```

**Two nodes. One conditional edge. That is the entire graph.**

The `agent_node` is the brain. The `tool_executor_node` is the hands. A conditional router after `agent_node` decides at each step: does Claude want to call a tool (→ `tool_executor_node`) or is it done (→ `END`)?

---

## 4. Key Concept: The ReAct Loop

ReAct stands for **Reason + Act**. It is the standard pattern behind almost every practical agent. This project makes the pattern visible by printing each phase to the console.

```
Question arrives
      │
      ▼
┌─────────────────────────────────────────────────────┐
│  REASON: Claude reads the question and its message  │
│  history. It decides: "I need to look up S3         │
│  security best practices first."                    │
└────────────────────────┬────────────────────────────┘
                         │ emits a tool_call
                         ▼
┌─────────────────────────────────────────────────────┐
│  ACT: tool_executor calls                           │
│  search_best_practices(topic="S3",                  │
│                        category="security")         │
└────────────────────────┬────────────────────────────┘
                         │ returns tool result
                         ▼
┌─────────────────────────────────────────────────────┐
│  OBSERVE: result is appended to message history     │
│  as a ToolMessage. Claude now sees it in the next   │
│  agent_node invocation.                             │
└────────────────────────┬────────────────────────────┘
                         │
                         ▼
             (loop repeats 1–3 more times)
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│  REASON: "I now have best practices and compliance  │
│  data. I will call format_report() to compose the  │
│  final answer."                                     │
└────────────────────────┬────────────────────────────┘
                         │ emits a tool_call to format_report
                         ▼
              [format_report result appended]
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│  REASON: "The report is ready. I will respond with  │
│  an AIMessage (no tool_call). I am done."           │
└────────────────────────┬────────────────────────────┘
                         │ no tool_call → router routes to END
                         ▼
                    Final answer printed
```

---

## 5. Agent State

The state is a plain Python `TypedDict`. Every node reads from it and returns an update. LangGraph merges updates automatically.

```
AgentState
├── messages: Annotated[list[AnyMessage], add_messages]
│   │
│   │  The single source of truth. Grows with every turn:
│   │    HumanMessage  ← the original question
│   │    AIMessage     ← Claude's reasoning / tool call decisions
│   │    ToolMessage   ← results returned by each tool
│   │    AIMessage     ← Claude's final natural-language answer
│   │
│   └─ add_messages reducer: LangGraph appends, never overwrites
│
└── iteration_count: int
    │
    └─ Safety counter. If the loop runs more than MAX_ITERATIONS
       (default: 6) the graph raises a clear error so learners
       can see exactly what an infinite-loop guard looks like.
```

`messages` is the only field that uses a reducer (`add_messages`). Every other field is replaced on each update. This is an important LangGraph detail — learners must understand that reducers control *how* a field is merged, not just *what* goes in it.

---

## 6. Tools

Three tools are defined. Each is a plain Python function decorated with `@tool` from `langchain_core.tools`. Claude sees the function name, docstring, and typed parameters — they are its only interface to the outside world.

### Tool 1 — `search_best_practices`

```
search_best_practices(topic: str, category: str) -> str
```

**What it does:** Looks up best-practice guidance from a local in-memory dictionary (no network call). The dictionary is pre-populated with ~10 topics covering S3, IAM, VPC, EC2, RDS, Lambda, Terraform state, and Kubernetes.

**Why in-memory?** Zero external dependencies. The learner can run this offline and always gets predictable output. The dict is stored in `data/knowledge_base.py` and is easy to inspect and extend.

**Example input/output:**
```
Input:  topic="S3", category="security"
Output: "Enable S3 Block Public Access at the account level. Use bucket policies
         with deny conditions for unencrypted uploads (aws:SecureTransport).
         Enable SSE-KMS encryption with a customer-managed key. Enable S3
         access logging to a separate audit bucket. ..."
```

### Tool 2 — `check_compliance_rules`

```
check_compliance_rules(service: str, rule_type: str) -> str
```

**What it does:** Returns compliance mappings from a local dictionary. `rule_type` accepts `"cis"`, `"well_architected"`, or `"nist"`. Pre-populated for the same set of cloud services.

**Example input/output:**
```
Input:  service="S3", rule_type="cis"
Output: "CIS AWS 2.1.2 — Ensure S3 Bucket Policy is set to deny HTTP requests.
         CIS AWS 2.1.5 — Ensure that S3 Buckets are configured with
         'Block public access'. CIS AWS 2.1.4 — Ensure that S3 Buckets have
         object-level logging enabled in CloudTrail. ..."
```

### Tool 3 — `format_report`

```
format_report(question: str, best_practices: list[str], compliance_rules: list[str]) -> str
```

**What it does:** Receives the collected findings and formats them into a structured Markdown advisory report with sections: Summary, Best Practices, Compliance Requirements, and Next Steps. This is a pure formatting function — no LLM call inside.

**Why a separate tool?** It makes the agent's intent explicit: Claude must *decide* to call `format_report`, passing in exactly the information it gathered. Learners can see Claude assembling the final output from its prior observations rather than just printing whatever it was going to say.

---

## 7. Nodes

### Node 1 — `agent_node`

Responsibilities:
- Receives the current `AgentState`.
- Increments `iteration_count`; raises `RuntimeError` if it exceeds `MAX_ITERATIONS`.
- Calls the Claude model (bound with all three tools) passing `state["messages"]`.
- Returns `{"messages": [ai_message], "iteration_count": new_count}`.

The Claude model is initialised with `.bind_tools(tools)`. This tells the model the tool schemas and allows it to emit `tool_calls` inside `AIMessage`.

### Node 2 — `tool_executor_node`

Responsibilities:
- Reads the last `AIMessage` from `state["messages"]`.
- Iterates over every `tool_call` in that message (Claude can request multiple tools in one turn).
- Dispatches to the matching Python function from a `{name: function}` registry.
- Wraps each result in a `ToolMessage` (preserving `tool_call_id` for traceability).
- Returns `{"messages": [tool_message, ...]}`.

LangGraph's `add_messages` reducer appends these `ToolMessage` objects to the existing list, so the full conversation history is always intact.

---

## 8. Graph Structure and Routing

```python
graph = StateGraph(AgentState)

graph.add_node("agent",         agent_node)
graph.add_node("tool_executor", tool_executor_node)

graph.add_edge(START, "agent")

graph.add_conditional_edges(
    "agent",
    route_after_agent,          # the router function
    {
        "call_tools": "tool_executor",
        "end":        END,
    }
)

graph.add_edge("tool_executor", "agent")  # always loops back
```

### The Router Function

```
route_after_agent(state: AgentState) -> str
```

Inspects the last message in `state["messages"]`. Returns:
- `"call_tools"` — if the message is an `AIMessage` with a non-empty `tool_calls` list.
- `"end"` — if the message is an `AIMessage` with no `tool_calls` (Claude is done reasoning).

This is the *only* decision point in the graph. Everything else is deterministic.

---

## 9. Execution Flow — Concrete Walkthrough

**Input question:** `"What are the best practices for securing an S3 bucket that stores sensitive customer data?"`

| Step | Node | What happens | State after |
|------|------|-------------|-------------|
| 1 | START | Graph initialises `AgentState` with `HumanMessage(question)` | `messages=[HumanMessage]`, `iteration_count=0` |
| 2 | `agent_node` | Claude receives the `HumanMessage`. Reasons: needs best practices. Emits `AIMessage(tool_calls=[search_best_practices(topic="S3", category="security")])` | `messages=[HM, AI]`, `count=1` |
| 3 | Router | `AIMessage` has tool_calls → routes to `tool_executor` | — |
| 4 | `tool_executor_node` | Calls `search_best_practices("S3","security")`. Returns `ToolMessage` with results | `messages=[HM, AI, TM]` |
| 5 | `agent_node` | Claude sees the best-practices text. Reasons: now needs compliance. Emits `AIMessage(tool_calls=[check_compliance_rules(service="S3", rule_type="cis")])` | `messages=[HM, AI, TM, AI]`, `count=2` |
| 6 | Router | `AIMessage` has tool_calls → `tool_executor` | — |
| 7 | `tool_executor_node` | Calls `check_compliance_rules("S3","cis")`. Returns `ToolMessage` | `messages=[..., TM]` |
| 8 | `agent_node` | Claude has both inputs. Emits `AIMessage(tool_calls=[format_report(...)])` | `count=3` |
| 9 | Router | `AIMessage` has tool_calls → `tool_executor` | — |
| 10 | `tool_executor_node` | Calls `format_report(...)`. Returns `ToolMessage` with formatted report | `messages=[..., TM]` |
| 11 | `agent_node` | Claude reads the formatted report. Emits a plain `AIMessage` (no tool_calls) with a one-paragraph human summary | `count=4` |
| 12 | Router | No tool_calls → routes to END | — |
| 13 | END | Final `AIMessage` is printed. Total turns: 4 (well within `MAX_ITERATIONS=6`) | done |

---

## 10. Technology Stack

| Component | Choice | Version | Why |
|-----------|--------|---------|-----|
| Orchestration | LangGraph | `>=0.2` | Industry-standard graph-based agent framework; explicit state makes the loop visible |
| LLM | `claude-haiku-4-5` (default) | latest | Fast and cheap for a learning demo; easy to swap to `claude-sonnet-4-6` via env var |
| LLM SDK | `langchain-anthropic` | `>=0.3` | Official LangChain integration for Claude; handles tool-binding and message formatting |
| Tool decoration | `langchain_core.tools.tool` | bundled | Zero boilerplate; turns any typed Python function into a tool schema |
| Python | 3.11+ | 3.11 | Required by LangGraph typed-dict features |
| Config | `python-dotenv` | `>=1.0` | Loads `ANTHROPIC_API_KEY` from a `.env` file; learner does not touch shell environment |

No database, no vector store, no external APIs beyond the Anthropic endpoint.

---

## 11. Project File Structure

```
agentic-ai-langgraph-demo/
│
├── SPEC.md                    ← this document
│
├── .env.example               ← template: ANTHROPIC_API_KEY=sk-ant-...
├── requirements.txt           ← pinned dependencies
│
├── agent/
│   ├── __init__.py
│   ├── state.py               ← AgentState TypedDict definition
│   ├── tools.py               ← all three @tool functions
│   ├── nodes.py               ← agent_node, tool_executor_node
│   ├── router.py              ← route_after_agent function
│   └── graph.py               ← graph assembly + compile()
│
├── data/
│   └── knowledge_base.py      ← in-memory best-practices + compliance dicts
│
└── main.py                    ← entry point; accepts question as CLI arg or interactive prompt
```

Every file is small and single-purpose. A learner can read each file independently and understand exactly one concept.

---

## 12. Conceptual Map — LangGraph Primitives

This table maps LangGraph vocabulary to plain English and to the concrete objects in this project.

| LangGraph term | Plain English | This project's instance |
|----------------|--------------|------------------------|
| `StateGraph` | The container that holds all nodes and edges | `graph = StateGraph(AgentState)` in `graph.py` |
| `TypedDict` (state) | A typed snapshot passed between nodes; LangGraph merges updates | `AgentState` in `state.py` |
| Reducer (`add_messages`) | A function that controls how a state field is updated (append vs replace) | Applied to `messages` field only |
| Node | A Python function that receives state and returns a partial update | `agent_node`, `tool_executor_node` |
| Edge | A fixed connection between two nodes | `tool_executor → agent` |
| Conditional edge | A connection whose target is decided at runtime by a router function | `agent → {call_tools, end}` |
| `START` / `END` | Built-in sentinel nodes marking graph entry and exit | `graph.add_edge(START, "agent")` |
| `graph.compile()` | Produces a `CompiledGraph` (a runnable object) | called at the bottom of `graph.py` |
| `compiled_graph.invoke(input)` | Runs the graph from START to END with the given initial state | called in `main.py` |

---

## 13. What Makes This "Agentic"

A traditional pipeline executes a fixed, pre-determined sequence of steps. An agent is different in three ways that this project makes explicit:

1. **Dynamic planning.** Claude decides *which* tools to call and *in what order*, based on what it has learned so far. You will see it call `check_compliance_rules` only after reading the best-practices results — not before.

2. **Self-termination.** Nobody tells Claude when to stop. It stops when its own reasoning determines that the information it has is sufficient. The router detects this by checking for the absence of `tool_calls`.

3. **State-accumulating loop.** Each iteration the agent has *more context* than the previous one. The `messages` list grows and Claude's next decision is informed by everything that came before. This is not a chain — it is a feedback loop.

---

## 14. Learning Extensions (post-demo ideas)

Once the base demo runs, these are natural next steps to deepen understanding — in increasing order of complexity:

| Extension | New concept introduced |
|-----------|----------------------|
| Add a 4th tool: `web_search()` (mock) | Tool registry, dynamic dispatch |
| Add a `HumanFeedbackMessage` node between tool_executor and agent | Human-in-the-loop interrupts |
| Replace the in-memory dict with a local JSON file | External I/O inside a tool |
| Add a `max_iterations` early-exit path that still returns a partial report | Graceful degradation |
| Swap Claude model via env var at runtime | Model-agnostic design |
| Enable `graph.stream()` instead of `invoke()` to print intermediate steps live | Streaming / observability |
| Add LangSmith tracing with one env var | Production-grade observability |
| Build a second agent that calls this one as a sub-graph | Multi-agent orchestration |

---

## 15. Implementation Phases

When implementation begins, the work is sequenced as follows:

| Phase | Deliverable | Estimated scope |
|-------|------------|-----------------|
| 1 | `data/knowledge_base.py` + `agent/state.py` | ~60 lines |
| 2 | `agent/tools.py` (all 3 tools) | ~80 lines |
| 3 | `agent/nodes.py` (both nodes) | ~60 lines |
| 4 | `agent/router.py` + `agent/graph.py` | ~40 lines |
| 5 | `main.py` + `.env.example` + `requirements.txt` | ~30 lines |
| 6 | End-to-end smoke test with a sample question | validation |

Total estimated implementation: **~270 lines of Python** across 8 files. Each phase produces independently testable code.

---

## 16. Sample Interaction (expected console output)

```
$ python main.py

Enter your infrastructure question: What are the best practices for securing
an S3 bucket that stores sensitive customer data?

--- Agent starting ---

[Iteration 1] Claude is reasoning...
  → Tool call: search_best_practices(topic='S3', category='security')
  ✓ Tool result received (342 chars)

[Iteration 2] Claude is reasoning...
  → Tool call: check_compliance_rules(service='S3', rule_type='cis')
  ✓ Tool result received (278 chars)

[Iteration 3] Claude is reasoning...
  → Tool call: format_report(question='...', best_practices=[...], compliance_rules=[...])
  ✓ Tool result received (891 chars)

[Iteration 4] Claude is reasoning...
  → No tool call. Agent is done.

--- Final Advisory Report ---

## S3 Security Advisory Report

**Question:** What are the best practices for securing an S3 bucket that stores
sensitive customer data?

### Summary
Based on AWS best practices and CIS Benchmark requirements, securing an S3 bucket
for sensitive data requires controls across access, encryption, logging, and
network isolation...

### Best Practices
1. Enable S3 Block Public Access at account level
2. Use bucket policies with `aws:SecureTransport` deny condition
3. Enable SSE-KMS with a customer-managed key (CMK)
...

### CIS Compliance Requirements
- CIS AWS 2.1.2 — Deny HTTP requests via bucket policy
- CIS AWS 2.1.5 — Block all public access
...

### Recommended Next Steps
1. Run `aws s3api get-bucket-policy` to audit your current policy
2. Enable CloudTrail S3 object-level logging
3. Review IAM roles for least-privilege access

--- Agent completed in 4 iterations ---
```

---

*End of specification. Ready for implementation on approval.*
