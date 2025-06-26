from typing import TypedDict
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from dotenv import load_dotenv

load_dotenv()


class AgentState(TypedDict):
    messages: list[HumanMessage | AIMessage]


llm = ChatOpenAI(model="gpt-4o")


def proceess(state: AgentState) -> AgentState:
    """This node will solve the request you input"""
    response = llm.invoke(state["messages"])

    state["messages"].append(AIMessage(content=response.content))
    print(f"\nAI: {response.content}")

    return state


graph = StateGraph(AgentState)

graph.add_node("proceess", proceess)
graph.add_edge(START, "proceess")
graph.add_edge("proceess", END)

agent = graph.compile()

conversation_hisotry = []

while True:
    user_input = input("Enter: ")
    if user_input.lower() == "bye":
        break
    conversation_hisotry.append(HumanMessage(content=user_input))
    result = agent.invoke({"messages": conversation_hisotry})
    conversation_hisotry = result["messages"]

with open("logging.txt", "w") as file:
    file.write("Your Conversation Log:\n\n")

    for message in conversation_hisotry:
        if isinstance(message, HumanMessage):
            file.write(f"You: {message.content}\n")
        elif isinstance(message, AIMessage):
            file.write(f"AI: {message.content}\n\n")

    file.write("End of Conversation\n")

print("Conversation saved to logging.txt")
