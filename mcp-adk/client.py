# 导入基础库
import os
from google.adk.models.lite_llm import LiteLlm
from google.adk.agents.llm_agent import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters

DS_API_KEY = os.getenv("DS_API_KEY")
DS_BASE_URL = os.getenv("DS_BASE_URL")

model = LiteLlm(model="deepseek/deepseek-chat", api_base=DS_BASE_URL, api_key=DS_API_KEY)
os.environ["HTTP_PROXY"] = "http://127.0.0.1:10080"
os.environ["HTTPS_PROXY"] = "http://127.0.0.1:10080"


# --- Step 1: 创建导入MCP工具函数 ---
async def get_tools_async():
    """Gets tools from the File System MCP Server."""
    print("Attempting to connect to MCP Filesystem server...")
    tools, exit_stack = await MCPToolset.from_server(
        # Use StdioServerParameters for local process communication
        connection_params=StdioServerParameters(
            command="python3",  # Command to run the server
            args=["/root/autodl-tmp/MCP/temp-test-mcp/server.py"],
        )
    )
    print("MCP Toolset created successfully.")
    # MCP需要维护一个与本地MCP服务器的连接。
    # exit_stack管理这个连接的清理。
    return tools, exit_stack


# --- Step 2: 创建ADK Agent ---
async def create_agent():
    """Gets tools from MCP Server."""
    tools, exit_stack = await get_tools_async()

    agent = LlmAgent(
        model="gemini-2.0-flash",
        name="filesystem_assistant",
        instruction="Help user interact with the local filesystem using available tools.",
        tools=tools,
    )
    return agent, exit_stack


root_agent = create_agent()
