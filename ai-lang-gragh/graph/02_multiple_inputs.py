from typing import List, TypedDict
from langgraph.graph import StateGraph
from functools import reduce
import operator


class AgentState(TypedDict):
    values: List[int]
    name: str
    answer: str
    operation: str


def process_values(state: AgentState) -> AgentState:
    """This function hanldes multiple different inputs"""

    if state["operation"] == "*":
        answer = reduce(operator.mul, state["values"])
    else:
        answer = sum(state["values"])

    state["answer"] = f"Hi there {state['name']}! Your answer = {answer}"
    return state


graph = StateGraph(AgentState)

graph.add_node("processor", process_values)

graph.set_entry_point("processor")
graph.set_finish_point("processor")

app = graph.compile()

answers = app.invoke({"name": "Bob", "values": [1, 2, 3, 4], "operation": "*"})

print(answers["answer"])
