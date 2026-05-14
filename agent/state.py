from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage

# The agent stops and raises RuntimeError if it exceeds this many iterations.
# This is intentionally visible — learners should see what an infinite-loop guard looks like.
MAX_ITERATIONS = 6


class AgentState(TypedDict):
    # add_messages is a reducer: it APPENDS new messages rather than replacing the list.
    # Every HumanMessage, AIMessage, and ToolMessage accumulates here across iterations.
    messages: Annotated[list[AnyMessage], add_messages]

    # Plain int — replaced (not appended) on every agent_node call.
    # Demonstrates that only fields with reducers accumulate; all others are overwritten.
    iteration_count: int
