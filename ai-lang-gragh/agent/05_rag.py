import os
from dotenv import load_dotenv
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import SystemMessage, BaseMessage, ToolMessage, HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.graph import StateGraph, END
from langgraph.graph.message import StateGraph, add_messages
from langgraph.prebuilt import ToolNode

load_dotenv()

llm = ChatOpenAI(model="gpt-4o", temperature=0)

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
)

pdf_path = "labubu.pdf"


if not os.path.exists(pdf_path):
    raise FileNotFoundError(f"PDF file not found: {pdf_path}")

pdf_loader = PyPDFLoader(pdf_path)

try:
    pages = pdf_loader.load()
    print(f"PDF has been loaded and has {len(pages)} pages")
except Exception as e:
    print(f"Error loading PDF: {e}")
    raise

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
)

pages_split = text_splitter.split_documents(pages)

persist_dir = "vector_db"
collection_name = "labubu"


if not os.path.exists(persist_dir):
    os.makedirs(persist_dir)

try:
    vectorstore = Chroma.from_documents(
        documents=pages_split,
        embedding=embeddings,
        persist_directory=persist_dir,
        collection_name=collection_name,
    )
    print(f"Created ChromaDB vector store!")

except Exception as e:
    print(f"Error setting up ChromaDB: {str(e)}")
    raise

retriever = vectorstore.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 5},
)


@tool
def retriever_tool(query: str) -> str:
    """
    This tool searches and returns the information from the labubu document.
    """
    docs = retriever.invoke(query)

    if not docs:
        return "I found no relevant information int the labubu document."

    results = []

    for i, doc in enumerate(docs):
        results.append(f"Document {i+1}:\n {doc.page_content}")

    return "\n\n".join(results)


tools = [retriever_tool]

llm = llm.bind_tools(tools)


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


def should_continue(state: AgentState):
    """Check if the last message contains tool calls."""
    result = state["messages"][-1]
    return hasattr(result, "tool_calls") and len(result.tool_calls) > 0


system_prompt = """
You are an intelligent AI assistant who answers questions about labubu based on the PDF document loaded into your knowledge base.
Use the retriever tool available to answer questions about the labubu data. You can make multiple calls if needed.
If you need to look up some information before asking a follow up question, you are allowed to do that!
Please always cite the specific parts of the documents you use in your answers.
"""

tools_dict = {tool.name: tool for tool in tools}


def call_llm(state: AgentState) -> AgentState:
    """Function to call the LLM with the current state"""
    messages = list(state["messages"])
    messages = [SystemMessage(content=system_prompt)] + messages
    messages = llm.invoke(messages)
    return {"messages": messages}


def take_action(state: AgentState) -> AgentState:
    """Execute tool calls from the LLM's response"""

    tool_calls = state["messages"][-1].tool_calls
    results = []

    for t in tool_calls:
        print(f"Calling Tool: {t["name"]} with query: {t['args'].get("queery","No query provide")}")
        if not t["name"] in tools_dict:
            print(f"\nTool: {t['name']} does not exist.")
            result = (
                "Incorrect Tool Name, Please Retry and Select tool from List of Available tools."
            )
        else:
            result = tools_dict[t["name"]].invoke(t["args"].get("query", ""))
            print(f"Result length: {len(str(result))}")

        results.append(
            ToolMessage(tool_call_id=t["id"], name=t["name"], content=str(result)),
        )

    print("Tools Execution Complete. Back to the model!")
    return {"messages": results}


graph = StateGraph(AgentState)

graph.add_node("llm", call_llm)
graph.add_node("retriever_agent", take_action)

graph.add_conditional_edges(
    "llm",
    should_continue,
    {
        True: "retriever_agent",
        False: END,
    },
)
graph.add_edge("retriever_agent", "llm")
graph.set_entry_point("llm")

app = graph.compile()


def run_agent():
    print("\n=== RAG AGENT ===")
    while True:
        user_input = input("\nQuery: ")
        if user_input.lower() in ["exit", "quit", "bye"]:
            break

        messages = [HumanMessage(content=user_input)]
        result = app.invoke({"messages": messages})
        print("\n=== ANSWER ===")
        print(result["messages"][-1].content)


if __name__ == "__main__":
    run_agent()
