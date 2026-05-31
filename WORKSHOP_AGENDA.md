# Cloud Infrastructure Advisory Agent — 3-Hour Workshop Agenda

**Target Audience:** Cloud/DevOps Engineers new to agentic AI  
**Duration:** 180 minutes (3 hours)  
**Prerequisites:** Python 3.11+, basic familiarity with AWS services, text editor/IDE

---

## Pre-Workshop Setup (Attendees: 15 minutes before start)

Send attendees this checklist before the workshop:

- [ ] Clone the repository: `git clone <repo-url> && cd agentic-ai-langgraph-demo`
- [ ] Ensure Python 3.11+ is installed: `python --version`
- [ ] Create an Anthropic API key at https://console.anthropic.com/
- [ ] Copy `.env.example` to `.env` and paste your API key
- [ ] Verify setup: `uv run python main.py "What is S3 versioning?"` (should complete without errors)

**Facilitator tip:** Test the pre-flight checklist in your own environment 24 hours before the workshop.

---

## Workshop Timeline

### 📍 **Session 1: Understanding Agentic AI (0:00 – 0:45 | 45 min)**

#### Part 1A: What is an Agent? (0:00 – 0:15 | 15 min)

**Instructor-led presentation** (slides + live demo)

- **What makes AI "agentic"?** (3 min)
  - Autonomous decision-making
  - Tool calling (the agent chooses *which* tool to use and *why*)
  - Multi-step reasoning without human intervention
  - Deterministic termination (knows when to stop)

- **Real-world scenario** (2 min)
  - A DevOps engineer asks: *"What are the best practices for securing an S3 bucket?"*
  - Without an agent: manually search AWS docs, RFC summaries, compliance frameworks
  - With an agent: ChatBot autonomously gathers info, synthesizes it, returns structured advisory

- **Live demo: Run the agent** (10 min)
  - Show the console output as the agent runs
  - Highlight the **ReAct loop** in real time:
    - "REASON" → Claude decides to call `search_best_practices`
    - "ACT" → Tool executes
    - "OBSERVE" → Result is appended to message history
    - Loop repeats 2–3 more times
  - Emphasize: *No hardcoded workflow; Claude is making all decisions.*

**Attendee activity:** Have everyone run the agent in their terminal (guided):
```bash
cd agentic-ai-langgraph-demo
uv run python main.py "What are the best practices for securing an S3 bucket?"
```
Pair-share observations: *What did the agent do? How many tool calls did it make?*

#### Part 1B: Core Concepts Explained (0:15 – 0:45 | 30 min)

**Concept 1: Agent State (5 min)**
- What is it? A TypedDict carrying messages + metadata through the graph
- Why it matters? It's the single source of truth; every step reads it and updates it
- Show structure:
  ```
  AgentState {
    messages: [HumanMessage, AIMessage, ToolMessage, ...]  ← grows each turn
    iteration_count: int
  }
  ```
- Attendee task: Open [agent/state.py](agent/state.py), highlight the `add_messages` reducer

**Concept 2: Tool Calling (5 min)**
- What is it? The agent (Claude) dynamically decides which function to invoke
- Three tools in this demo:
  - `search_best_practices(topic, category)` — looks up S3/IAM/VPC best practices
  - `check_compliance_rules(service, rule_type)` — retrieves CIS/NIST/Well-Architected rules
  - `format_report(question, best_practices, compliance)` — composes final advisory
- Why it matters? Separates agent reasoning from deterministic function execution
- Attendee task: Open [agent/tools.py](agent/tools.py), identify the `@tool` decorators

**Concept 3: The ReAct Loop (10 min)**
- ReAct = **Reason** → **Act** → **Observe** (repeat until done)
- Walk through the loop with a visual timeline:
  ```
  Agent: "I need S3 best practices."        ← REASON
    ↓
  Tool: search_best_practices called        ← ACT
    ↓
  Agent sees result in message history      ← OBSERVE
    ↓
  Agent: "I now need compliance rules."     ← REASON again
    ↓
  Tool: check_compliance_rules called       ← ACT again
    ↓
  ...repeat until Claude says "I'm done"
  ```
- Attendee task: Trace through [agent/nodes.py](agent/nodes.py) (agent_node and tool_executor_node)

**Concept 4: The LangGraph Graph (10 min)**
- **What is it?** A state machine with nodes and edges
- **Two nodes:**
  - `agent_node` — Claude thinks (reason + decide tool or stop)
  - `tool_executor_node` — Execute the tool Claude chose
- **One conditional router:**
  - If Claude's last message has `tool_calls` → route to `tool_executor_node`
  - Else → route to `END`
- Show the graph diagram from [SPEC.md](SPEC.md) (Section 3)
- Attendee task: Open [agent/graph.py](agent/graph.py) and [agent/router.py](agent/router.py), identify:
  - `add_node()` calls
  - `add_conditional_edges()` and the conditional router logic

**Break (Optional: 2–3 min water/coffee)**

---

### 📍 **Session 2: Code Deep Dive (0:45 – 1:45 | 60 min)**

#### Part 2A: Tracing a Question Through the Agent (0:45 – 1:15 | 30 min)

**Instructor-led walkthrough** (live code, breakpoints optional)

Scenario: Attendee asks the agent: *"What are the CIS compliance controls for IAM?"*

1. **Step 1: Message enters the graph** (2 min)
   - Look at [main.py](main.py): `HumanMessage` is created
   - State is initialized with this message
   - Open [agent/graph.py](agent/graph.py): show `compiled_graph.invoke()`

2. **Step 2: Agent node runs** (5 min)
   - Open [agent/nodes.py](agent/nodes.py), look at `agent_node()`
   - Trace: message history is passed to Claude (via `ChatAnthropic`)
   - Claude decides: *"I should call `check_compliance_rules('IAM', 'cis')`"*
   - Show the code that emits `AIMessage(tool_calls=[...])`
   - Emphasize: **Claude made this decision; it is not hardcoded**

3. **Step 3: Router evaluates** (2 min)
   - Open [agent/router.py](agent/router.py)
   - Router checks: is `tool_calls` non-empty? YES
   - Route to `tool_executor_node`

4. **Step 4: Tool executor runs** (5 min)
   - Open [agent/nodes.py](agent/nodes.py), look at `tool_executor_node()`
   - Trace: tool name is extracted from the `AIMessage.tool_calls`
   - Tool is dispatched via `_TOOL_REGISTRY` (a simple dict)
   - Result is wrapped in a `ToolMessage` and appended to state

5. **Step 5: Loop back to agent node** (3 min)
   - State now has: `[HumanMessage, AIMessage, ToolMessage]`
   - Agent node runs again with this expanded history
   - Claude now sees the tool result and decides: *"I have the compliance data. I should call `format_report()`"*

6. **Step 6: Format report, then done** (8 min)
   - `format_report()` is called (a pure string-formatting function)
   - Claude's next iteration sees this result
   - Claude decides: *"I am done. I will respond with a plain AIMessage (no tool_calls)."*
   - Router sees no `tool_calls` → route to `END`
   - Final answer is printed

**Attendee activity:** Pair-and-trace
- Pair up attendees
- Give each pair a printed or projected version of the code flow
- Ask: *Trace the path of a question through the agent. At which line does the router make its decision?*

#### Part 2B: Understanding the Knowledge Base (1:15 – 1:45 | 30 min)

**Hands-on code review**

- Open [data/knowledge_base.py](data/knowledge_base.py)
- Show the two main dictionaries:
  - `BEST_PRACTICES`: `{ (topic, category) → str }`
  - `COMPLIANCE_RULES`: `{ (service, rule_type) → str }`
- Highlight: **Why no network calls?**
  - Deterministic offline behavior (great for learning)
  - No API latency surprises
  - Perfect reproducibility for debugging
- **Attendee task: Add a new entry**
  1. Pick a service (e.g., `Lambda`) and a category (e.g., `cost_optimization`)
  2. Write a short best-practice summary (3–4 sentences)
  3. Add it to `BEST_PRACTICES` dict
  4. Save and run: `uv run python main.py "What are cost-optimization best practices for Lambda?"`
  5. Watch the agent use your new entry

**Facilitator tip:** Have attendees copy their new entries to a shared doc so they can see the collective knowledge base grow.

---

### 📍 **Session 3: Hands-On Experiments & Extensions (1:45 – 2:55 | 70 min)**

#### Part 3A: Experiment 1 — Watch the MAX_ITERATIONS Guard Fire (1:45 – 2:05 | 20 min)

**Learning goal:** Understand termination conditions and failure modes.

**Setup:**
- Open [agent/nodes.py](agent/nodes.py), find `MAX_ITERATIONS = 6`
- This guard prevents infinite loops
- When the loop would exceed 6 iterations, it raises `RuntimeError`

**Attendee task:**
1. Ask the agent a **vague, open-ended question** that forces many reasoning steps:
   ```bash
   uv run python main.py "What is the relationship between IAM, S3, and VPC security?"
   ```
2. Watch the iteration counter in the console output
3. If it reaches 6, the agent stops with a `RuntimeError`
4. **Discussion:** Why is this guard useful? What does it teach learners?
   - Prevents infinite loops
   - Makes learners aware that agents have limits
   - Forces explicit thinking about termination

**Facilitator note:** This is intentional. The error message is part of the learning. Do not silently cap the iterations.

#### Part 3A (continued): Experiment 2 — Try Single-Shot Mode (2:05 – 2:20 | 15 min)

**Learning goal:** Understand different invocation modes.

- Open [main.py](main.py), observe the CLI mode:
  ```python
  if len(sys.argv) > 1:
      question = sys.argv[1]
      # Single-shot mode
  ```
- Run: `uv run python main.py "What is S3 versioning?"`
- Observe: Agent runs non-interactively, prints result, exits
- **Attendee task:** Compare this to interactive mode:
  ```bash
  uv run python main.py
  # Type: What is IAM?
  # Type: exit
  ```
- **Discussion:** When would single-shot vs. interactive be preferable?

#### Part 3B: Experiment 3 — Modify a Tool's Behavior (2:20 – 2:45 | 25 min)

**Learning goal:** Understand tool coupling to the agent; see how changes propagate.

**Scenario:** The compliance data for S3 is incomplete. Add a fake compliance rule.

**Attendee task (guided):**
1. Open [data/knowledge_base.py](data/knowledge_base.py)
2. Find the `COMPLIANCE_RULES` dict
3. Locate the entry for `("s3", "cis")`
4. Append a new line to the compliance string:
   ```python
   ("s3", "cis"): "... existing rules ... \n✓ NEW: Use Object Lock for retention.",
   ```
5. Save
6. Run: `uv run python main.py "What CIS rules apply to S3?"`
7. **Observe:** Your new rule is now in the agent's knowledge base
8. **Discussion:** 
   - How did the agent use it?
   - Did Claude mention your new rule in the final advisory?
   - What if you added conflicting rules?

#### Part 3B (continued): Experiment 4 — Change the Model (2:45 – 3:00 | 15 min)

**Learning goal:** Understand how model selection affects agent behavior.

**Setup:**
- Open [agent/nodes.py](agent/nodes.py), find the `ChatAnthropic` instantiation:
  ```python
  llm = ChatAnthropic(
      model=os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001"),
      ...
  )
  ```

**Attendee task:**
1. Run with the default model (Haiku):
   ```bash
   uv run python main.py "What is S3 encryption?"
   ```
   Note the iteration count and reasoning depth.

2. Run with Sonnet (more capable):
   ```bash
   CLAUDE_MODEL=claude-sonnet-4-6 uv run python main.py "What is S3 encryption?"
   ```
   Observe: Does Sonnet answer in fewer iterations? More detail? Different reasoning?

3. **Discussion:**
   - Trade-off: cost vs. reasoning depth
   - Why use Haiku for a tutorial? (Budget, speed, clarity for learners)
   - When would you choose Sonnet or a larger model in production?

---

### 📍 **Session 4: Synthesis & Q&A (2:55 – 3:00 | 5 min)**

**Facilitator recap:**
1. **What you learned today:**
   - Agent state flows through a graph
   - Tools enable autonomous decision-making
   - ReAct loop (Reason → Act → Observe) is the engine
   - LangGraph makes the loop explicit and debuggable
   - Termination conditions (MAX_ITERATIONS) prevent runaway agents

2. **Next steps for becoming an AI engineer:**
   - Try modifying the tools (add a new one, e.g., `search_aws_whitepapers()`)
   - Deploy the agent to a web API (e.g., FastAPI)
   - Scale beyond S3/IAM: add more domains (Kubernetes, Terraform, GCP)
   - Experiment with other frameworks (LangChain agents, Crew AI, Autogen)
   - Read research papers on ReAct, Chain-of-Thought, and agentic AI

3. **Open Q&A:** (5 min)
   - What questions came up during the experiments?
   - How would you extend this agent for your own use cases?

4. **Resources to take home:**
   - [SPEC.md](SPEC.md) — full technical spec
   - [CLAUDE.md](CLAUDE.md) — code guidance
   - Anthropic docs: https://docs.anthropic.com/
   - LangGraph docs: https://langchain-ai.github.io/langgraph/
   - LangChain tools: https://docs.langchain.com/docs/modules/tools

---

## Facilitator Notes

### Timing Buffers
- **Session 1** has built-in flexibility; if attendees are slow on code reading, you can trim the second part of 1B
- **Session 2** is critical; do not rush the code trace. It's the turning point where abstract concepts become concrete
- **Session 3** is highly interactive; timing depends on group pace and curiosity

### Equipment Checklist
- [ ] Projector / screenshare (live demo of agent running)
- [ ] Internet connection (Anthropic API calls; attendees download deps)
- [ ] Code editor visible on screen (VS Code, PyCharm, etc.)
- [ ] Optional: Printed code snippets or a handout of the key files

### Contingency Plans
- **If someone's setup fails:** Pair them with a neighbor or run the demo on your machine and have them watch
- **If time runs short:** Cut Part 3B Experiment 4 (model switching) — that's the most flexible segment
- **If attendees are advanced:** Propose a bonus challenge: *Implement a new tool that calls a real AWS API* (e.g., `describe_s3_buckets()`) and wire it into the graph

### Common Questions & Answers
- **Q: Can this agent run on local LLMs (not Claude)?**  
  A: The code uses `ChatAnthropic`, so not out of the box. But the same ReAct pattern works with `ChatOpenAI`, `ChatOllama`, etc. LangChain abstracts these.

- **Q: How is this different from ChatGPT plugins or function calling?**  
  A: Scope. ChatGPT can call one tool per turn. This agent can loop internally, calling multiple tools in sequence and reasoning about results.

- **Q: What if the agent gets stuck in a loop asking the same tool repeatedly?**  
  A: The `MAX_ITERATIONS` guard catches infinite loops. You could also add a deduplication check in the router.

- **Q: Can I use this in production?**  
  A: This is a learning demo, not production-ready. For production, add: error handling, retry logic, cost controls, user authentication, logging, observability.

---

## Post-Workshop

### Attendee Deliverables
- [ ] Successfully ran the agent locally
- [ ] Traced a question through the graph manually
- [ ] Added a new entry to the knowledge base
- [ ] Modified the model or tool behavior and observed the change

### Facilitator Follow-Up
- [ ] Send attendees the code, SPEC, and this agenda as a PDF
- [ ] Provide recordings (audio or screen) if possible
- [ ] Create a shared GitHub Discussion or Slack channel for follow-up questions
- [ ] Suggest a follow-up workshop: *Deploy this agent to a REST API* or *Build a multi-domain agent*

---

## References

- [SPEC.md](SPEC.md) — Full technical specification
- [CLAUDE.md](CLAUDE.md) — Code navigation guide
- [README.md](README.md) — Quick start
- [agent/graph.py](agent/graph.py) — Graph assembly
- [agent/nodes.py](agent/nodes.py) — Node logic
- [agent/tools.py](agent/tools.py) — Tool definitions
- [data/knowledge_base.py](data/knowledge_base.py) — Knowledge base
