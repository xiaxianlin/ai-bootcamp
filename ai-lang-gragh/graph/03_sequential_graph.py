from typing import TypedDict
from langgraph.graph import StateGraph


class AgentState(TypedDict):
    name: str
    age: str
    skills: list[str]
    final: str


def first_node(state: AgentState) -> AgentState:
    """This is the first node of our sequence"""
    state["final"] = f"{state['name']}, welcome to the system!"
    return state


def second_node(state: AgentState) -> AgentState:
    """This is the second node of our sequence"""
    state["final"] += f" You are {state['age']} years old!"
    return state


def third_node(state: AgentState) -> AgentState:
    """This is the third node of our sequence"""
    skills = ", ".join(state["skills"])
    state["final"] += f" You hava skills in: {skills}"
    return state


graph = StateGraph(AgentState)

graph.add_node("first", first_node)
graph.add_node("second", second_node)
graph.add_node("third", third_node)

graph.set_entry_point("first")
graph.add_edge("first", "second")
graph.add_edge("second", "third")
graph.set_finish_point("third")


app = graph.compile()

res = app.invoke({"name": "Bob", "age": 18, "skills": ["Python", "Java"]})
print(res["final"])
