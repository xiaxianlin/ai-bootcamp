from typing import TypedDict
from langgraph.graph import StateGraph, START, END


class AgentState(TypedDict):
    number1: int
    number2: int
    number3: int
    number4: int
    operation1: str
    operation2: str
    result1: int
    result2: int


def adder(state: AgentState) -> AgentState:
    """This node adds the 2 numbers"""
    state["result1"] = state["number1"] + state["number2"]
    return state


def subtractor(state: AgentState) -> AgentState:
    """This node substracts the 2 numbers"""
    state["result1"] = state["number1"] - state["number2"]
    return state


def adder2(state: AgentState) -> AgentState:
    """This node adds the 2 numbers and the last result"""
    state["result2"] = state["result1"] + state["number3"] + state["number4"]
    return state


def subtractor2(state: AgentState) -> AgentState:
    """This node substracts the 2 numbers and the last reulst"""
    state["result2"] = state["result1"] - state["number3"] - state["number4"]
    return state


def decide_next_node(state: AgentState) -> str:
    """This node will select the next node of the graph"""

    if state["operation1"] == "+":
        return "addition_operation"
    elif state["operation1"] == "-":
        return "subtraction_operation"


def decide_next_node2(state: AgentState) -> str:
    """This node will select the next node of the graph"""

    if state["operation2"] == "+":
        return "addition_operation2"
    elif state["operation2"] == "-":
        return "subtraction_operation2"


graph = StateGraph(AgentState)
graph.add_node("add_node", adder)
graph.add_node("substract_node", subtractor)
graph.add_node("add_node2", adder2)
graph.add_node("substract_node2", subtractor2)
graph.add_node("router", lambda state: state)
graph.add_node("router2", lambda state: state)

graph.add_edge(START, "router")
graph.add_conditional_edges(
    "router",
    decide_next_node,
    {
        # Edge: Node
        "addition_operation": "add_node",
        "subtraction_operation": "substract_node",
    },
)

graph.add_edge("add_node", "router2")
graph.add_edge("substract_node", "router2")

graph.add_conditional_edges(
    "router2",
    decide_next_node2,
    {
        # Edge: Node
        "addition_operation2": "add_node2",
        "subtraction_operation2": "substract_node2",
    },
)

graph.add_edge("add_node2", END)
graph.add_edge("substract_node2", END)

app = graph.compile()

init_state = AgentState(
    number1=10,
    number2=5,
    number3=7,
    number4=2,
    operation1="-",
    operation2="+",
)
res = app.invoke(init_state)
print(res)
