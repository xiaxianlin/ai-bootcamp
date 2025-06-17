import os
import sys
import json
import asyncio
from openai import OpenAI
from dotenv import load_dotenv
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()


class MultiServerMCPClient:
    def __init__(self):
        self.exit_stack = AsyncExitStack()
        self.openai_api_key = os.getenv("OPENAI_API_KEY")  # 读取 OpenAI API Key
        self.model = os.getenv("MODEL")  # 读取 model
        if not self.openai_api_key:
            raise ValueError("❌ 未找到 OpenAI API Key，请在 .env 文件中设置 OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.openai_api_key)

        self.sessions: dict[str, ClientSession] = {}
        self.tools_by_session: dict[str, list] = {}
        self.all_tools = []

    async def _start_one_server(self, script_path: str) -> ClientSession:
        """
        同时启动多个服务器并获取工具
        servers: 形如 {"weather": "weather_server.py", "rag": "rag_server.py"}
        """
        is_python = script_path.endswith(".py")
        is_js = script_path.endswith(".js")
        if not (is_python or is_js):
            raise ValueError("服务器脚本必须是 .py 或 .js 文件")

        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[script_path],
            env=None,
        )

        read_stream, write_stream = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        session = await self.exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )

        await session.initialize()

        return session

    async def connect_to_servers(self, servers: dict):
        """
        同时启动多个服务器并获取工具
        servers: 形如 {"weather": "weather_server.py", "rag": "rag_server.py"}
        """

        for server_name, script_path in servers.items():
            session = await self._start_one_server(script_path)
            self.sessions[server_name] = session

            resp = await session.list_tools()
            self.tools_by_session[server_name] = resp.tools

            for tool in resp.tools:
                function_name = f"{server_name}_{tool.name}"
                self.all_tools.append(
                    {
                        "type": "function",
                        "function": {
                            "name": function_name,
                            "description": tool.description,
                            "input_schema": tool.inputSchema,
                        },
                    }
                )

            self.all_tools = await self.transform_json(self.all_tools)

        print("\n✅ 已连接到下列服务器:")
        for name in servers:
            print(f"  - {name}: {servers[name]}")
        print("\n汇总的工具:")

        for t in self.all_tools:
            print(f"  - {t['function']['name']}")

    async def transform_json(self, json2_data):
        """
        将类似 json2 的格式转换为类似 json1 的格式，多余字段会被直接删除。

        :param json2_data: 一个可被解释为列表的 Python 对象（或已解析的 JSON 数据）
        :return: 转换后的新列表
        """
        result = []

        for item in json2_data:
            # 确保有 "type" 和 "function" 两个关键字段
            if not isinstance(item, dict) or "type" not in item or "function" not in item:
                continue

            old_func = item["function"]

            # 确保 function 下有我们需要的关键子字段
            if (
                not isinstance(old_func, dict)
                or "name" not in old_func
                or "description" not in old_func
            ):
                continue

            # 处理新 function 字段
            new_func = {
                "name": old_func["name"],
                "description": old_func["description"],
                "parameters": {},
            }

            # 读取 input_schema 并转成 parameters
            if "input_schema" in old_func and isinstance(old_func["input_schema"], dict):
                old_schema = old_func["input_schema"]

                # 新的 parameters 保留 type, properties, required 这三个字段
                new_func["parameters"]["type"] = old_schema.get("type", "object")
                new_func["parameters"]["properties"] = old_schema.get("properties", {})
                new_func["parameters"]["required"] = old_schema.get("required", [])

            new_item = {"type": item["type"], "function": new_func}

            result.append(new_item)

        return result

    async def chat_base(self, messages: list) -> list:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=self.all_tools,
        )

        if response.choices[0].finish_reason == "tool_calls":
            while True:
                messages = await self.create_function_response_messages(messages, response)
                response = self.client.chat.completions.create(
                    model=self.model, messages=messages, tools=self.all_tools
                )
                if response.choices[0].finish_reason != "tool_calls":
                    break

        return response

    async def create_function_response_messages(self, messages, response):
        function_call_messages = response.choices[0].message.tool_calls
        print(function_call_messages)
        messages.append(response.choices[0].message.model_dump())

        for function_call_message in function_call_messages:
            tool_name = function_call_message.function.name
            tool_args = json.loads(function_call_message.function.arguments)

            # 运行外部函数
            function_response = await self._call_mcp_tool(tool_name, tool_args)

            # 拼接消息队列
            messages.append(
                {
                    "role": "tool",
                    "content": function_response,
                    "tool_call_id": function_call_message.id,
                }
            )
        return messages

    async def process_query(self, query: str) -> str:
        """
        OpenAI 最新 Function Calling 逻辑:
        1. 发送用户消息 + tools 信息
        2. 若模型 `finish_reason == "tool_calls"`，则解析 toolCalls 并执行相应 MCP 工具
        3. 把调用结果返回给 OpenAI，让模型生成最终回答
        """
        messages = [{"role": "user", "content": query}]

        # 第一次请求
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=self.all_tools,
        )
        content = response.choices[0]
        print(content)
        print(self.all_tools)

        # 如果模型调用了 MCP 工具
        if content.finish_reason == "tool_calls":
            # 解析 tool_calls
            tool_call = content.message.tool_calls[0]
            tool_name = tool_call.function.name  # 形如 "weather_query_weather"
            tool_args = json.loads(tool_call.function.arguments)

            print(f"\n[ 调用工具: {tool_name}, 参数: {tool_args} ]\n")

            # 执行MCP工具
            result = await self._call_mcp_tool(tool_name, tool_args)

            # 把工具调用历史写进 messages
            messages.append(content.message.model_dump())
            messages.append(
                {
                    "role": "tool",
                    "content": result,
                    "tool_call_id": tool_call.id,
                }
            )
            # 第二次请求，让模型整合工具结果，生成最终回答
            response = self.client.chat.completions.create(model=self.model, messages=messages)
            return response.choices[0].message.content

        # 如果模型没调用工具，直接返回回答
        return content.message.content

    async def _call_mcp_tool(self, tool_full_name: str, tool_args: dict) -> str:
        """
        根据 "serverName_toolName" 调用相应的服务器工具
        """

        # 拆分 "weather_query_weather" -> ["weather", "query_weather"]
        parts = tool_full_name.split("_", 1)
        if len(parts) != 2:
            return f"无效的工具名称: {tool_full_name}"

        server_name, tool_name = parts
        session = self.sessions.get(server_name)
        if not session:
            return f"找不到服务器: {server_name}"

        # 执行 MCP 工具
        resp = await session.call_tool(tool_name, tool_args)
        return resp.content if resp.content else "工具执行无输出"

    async def chat_loop(self):
        """运行交互式聊天循环"""
        print("\nMCP 客户端已启动！输入 'quit' 退出")
        messages = []

        while True:
            query = input("\nQuery: ").strip()
            if query.lower() == "quit":
                break
            try:

                messages.append({"role": "user", "content": query})
                messages = messages[-20:]

                response = await self.chat_base(messages)
                messages.append(response.choices[0].message.model_dump())
                result = response.choices[0].message.content

                print(f"\n🤖: {result}")

            except Exception as e:
                print(f"\n⚠️ 发生错误: {str(e)}")

    async def cleanup(self):
        await self.exit_stack.aclose()


async def main():
    servers = {
        "weather": "weather_server.py",
        "SQLServer": "mysql_server.py",
        "PythonServer": "python_server.py",
    }

    client = MultiServerMCPClient()
    try:
        await client.connect_to_servers(servers)
        await client.chat_loop()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
