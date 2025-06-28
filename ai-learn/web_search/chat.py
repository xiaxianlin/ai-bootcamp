import json
from openai import OpenAI
from datetime import datetime

from tools.console import Console
from tools.search import SearchTool

from .prompts import SEARCH_SUMMARY_PROMPT, SEARCH_SYSTEM_PROMPT


search_tool = {
    "type": "function",
    "function": {
        "name": "search",
        "description": "使用谷歌搜索从互联网获取更多的实时信息",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "通过搜索从互联网获取的信息的问题、内容、关键词等",
                }
            },
            "required": ["query"],
        },
    },
}


class SearchBot:
    def __init__(self, model: str, base_url: str, api_key: str, serpapi_key: str):
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.model = model
        self.tools = [search_tool]
        self.search = SearchTool(serpapi_key)

    def _tools_description(self) -> str:
        """根据工具定义生成工具描述提示"""
        tool_descriptions = []

        for tool_def in self.tools:
            func = tool_def["function"]
            name = func["name"]
            desc = func["description"]
            params = []

            # 获取必需参数及其描述
            for param_name, param_info in func["parameters"]["properties"].items():
                if param_name in func["parameters"].get("required", []):
                    params.append(f"{param_name}，作用是：{param_info['description']}")

            tool_desc = (
                f"{name}，{desc}"
                f"{'，必须解析出来的参数是：' if params else ''}"
                f"{', '.join(params)}"
            )
            tool_descriptions.append(tool_desc)

        return "你现在可用的工具有：\n\n" + "\n".join(tool_descriptions)

    def _tools_handle(self, tool_calls, query):
        if not tool_calls:
            raise ValueError("没有工具调用")
        tool_call = tool_calls[0]
        func_name = tool_call.function.name
        func_args = tool_call.function.arguments
        print(f"检查需要进行工具调用，工具名称：{func_name}，工具参数：{func_args} ")
        if func_name != "search":
            raise ValueError("没有找到对应的工具")

        func_args = json.loads(func_args)
        results = self.search.search(**func_args)
        if not results:
            raise ValueError("工具调用失败")

        context = []
        for result in results:
            context.append(
                f"来源：{result['title']}\n"
                f"链接：{result['url']}\n"
                f"内容：{result['snippet']}\n"
            )

        search_data = {
            "type": "search_results",
            "total": len(results),
            "query": json.loads(tool_call.function.arguments)["query"],
            "results": results,
        }

        Console.log(json.dumps(search_data, indent=4))

        # 构造带上下文的提示
        context_prompt = SEARCH_SUMMARY_PROMPT.format(
            context="\n---\n".join(context),
            query=query,
            cur_date=datetime.now().strftime("%Y年%m月%d日"),
        )

        Console.log(context_prompt)
        return context_prompt

    def chat(self, query: str):
        """对话函数"""

        system_prompt = SEARCH_SYSTEM_PROMPT.format(tools_description=self._tools_description())

        Console.log(system_prompt)

        tool_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ]

        # 查询是否调用工具
        response = self.client.chat.completions.create(
            model=self.model, messages=tool_messages, tools=self.tools, tool_choice="auto"
        )

        choice = response.choices[0]

        # 不要调用工具
        if choice.finish_reason == "stop":
            print("未检测到需要调用工具，将直接进行输出\n")
            messages = [{"role": "user", "content": query}]

        # 需要调用工具，则去处理工具调用
        elif choice.finish_reason == "tool_calls":
            try:
                context_prompt = self._tools_handle(choice.message.tool_calls, query)
                messages = [{"role": "system", "content": context_prompt}]
            except Exception as e:
                print(f"工具调用失败：{str(e)}")
                messages = [{"role": "user", "content": query}]

        completion = self.client.chat.completions.create(
            model=self.model, messages=messages, stream=True
        )

        for chunk in completion:
            if chunk.choices and chunk.choices[0].delta.content:
                print(chunk.choices[0].delta.content, end="", flush=True)
