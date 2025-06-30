from typing import TypedDict, Annotated, Sequence
from dotenv import load_dotenv
from langchain_core.messages import SystemMessage, BaseMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.graph.message import StateGraph, add_messages
from langgraph.prebuilt import ToolNode


load_dotenv()


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


@tool
def add(a: int, b: int):
    """This ia an addition function that adds 2 numbers together"""
    return a + b


@tool
def substract(a: int, b: int):
    """This ia a substract function that adds 2 numbers together"""
    return a - b


@tool
def multiply(a: int, b: int):
    """This ia a multiply function that adds 2 numbers together"""
    return a * b


tools = [add, substract, multiply]

model = ChatOpenAI(model="gpt-4o").bind_tools(tools)


def model_call(state: AgentState) -> AgentState:
    system_prompt = SystemMessage(
        content="You are my AI assistant, please answer my query to the best of your ability"
    )
    response = model.invoke([system_prompt] + state["messages"])
    return {"messages": [response]}


def should_continue(state: AgentState) -> AgentState:
    messages = state["messages"]
    last_message = messages[-1]
    if not last_message.tool_calls:
        return "end"
    else:
        return "continue"


graph = StateGraph(AgentState)
graph.add_node("agent", model_call)

tool_node = ToolNode(tools=tools)
graph.add_node("tools", tool_node)

graph.set_entry_point("agent")
graph.add_conditional_edges(
    "agent",
    should_continue,
    {
        "continue": "tools",
        "end": END,
    },
)
graph.add_edge("tools", "agent")

app = graph.compile()


def print_stream(stream):
    for s in stream:
        message = s["messages"][-1]
        if isinstance(message, tuple):
            print(message)
        else:
            message.pretty_print()


inputs = {
    "messages": [
        # ("user", "Add 40 + 12.")
        ("user", "Add 40 + 12 and then multiply the result by 6. Also tell me a joke please.")
    ]
}

print_stream(app.stream(inputs, stream_mode="values"))
