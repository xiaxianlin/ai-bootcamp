from typing import TypedDict
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from dotenv import load_dotenv

load_dotenv()


class AgentState(TypedDict):
    messages: list[HumanMessage]


llm = ChatOpenAI(model="gpt-4o")


def proceess(state: AgentState) -> AgentState:

    response = llm.invoke(state["messages"])
    print(f"\nAI: {response.content}")

    return state


graph = StateGraph(AgentState)

graph.add_node("proceess", proceess)
graph.add_edge(START, "proceess")
graph.add_edge("proceess", END)

agent = graph.compile()

while True:
    user_input = input("Enter: ")
    if user_input.lower() == "bye":
        break
    agent.invoke({"messages": [HumanMessage(content=user_input)]})
