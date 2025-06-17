"""mcp_http_client.py – Async MCP client (Streamable HTTP)
===========================================================
• 完全移除 stdio 传输，改用 Streamable HTTP (POST + optional SSE)
• 支持 initialize → notifications/initialized → tools/list → tools/call
• 自动处理 line‑delimited JSON stream (application/json 或 text/event-stream)
• 保留交互式 chat_loop，兼容 OpenAI Function Calling
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv
from openai import OpenAI

################################################################################
# 通用配置加载
################################################################################


class Configuration:
    def __init__(self) -> None:
        load_dotenv()
        self.api_key = os.getenv("LLM_API_KEY")
        self.base_url = os.getenv("BASE_URL")
        self.model = os.getenv("MODEL", "gpt-4o")
        if not self.api_key:
            raise ValueError("❌ 未找到 LLM_API_KEY，请在 .env 文件中配置")

    @staticmethod
    def load_config(path: str) -> Dict[str, Any]:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)


################################################################################
# HTTP‑based MCP Server wrapper
################################################################################


class HTTPMCPServer:
    """与单个 MCP Streamable HTTP 服务器通信"""

    def __init__(self, name: str, endpoint: str) -> None:
        self.name = name
        self.endpoint = endpoint.rstrip("/")  # e.g. http://localhost:8000/mcp
        self.session: Optional[httpx.AsyncClient] = None
        self.protocol_version: str = "2024-11-05"

    async def initialize(self) -> None:
        self.session = httpx.AsyncClient(timeout=httpx.Timeout(30.0))
        # 1) initialize
        init_req = {
            "jsonrpc": "2.0",
            "id": 0,
            "method": "initialize",
            "params": {
                "protocolVersion": self.protocol_version,
                "capabilities": {},
                "clientInfo": {"name": "HTTP-MCP-Demo", "version": "0.1"},
            },
        }
        r = await self._post_json(init_req)
        if "error" in r:
            raise RuntimeError(f"Initialize error: {r['error']}")
        # 2) send initialized notification (no response expected)
        await self._post_json({"jsonrpc": "2.0", "method": "notifications/initialized"})

    async def list_tools(self) -> List[Dict[str, Any]]:
        req = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        res = await self._post_json(req)
        return res["result"]["tools"]

    async def call_tool_stream(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """调用工具并将流式结果拼接为完整文本"""
        req = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }
        assert self.session is not None
        async with self.session.stream(
            "POST", self.endpoint, json=req, headers={"Accept": "application/json"}
        ) as resp:
            if resp.status_code != 200:
                raise RuntimeError(f"HTTP {resp.status_code}")
            collected_text: List[str] = []
            async for line in resp.aiter_lines():
                if not line:
                    continue
                chunk = json.loads(line)
                if "stream" in chunk:
                    continue  # 中间进度
                if "error" in chunk:
                    raise RuntimeError(chunk["error"]["message"])
                if "result" in chunk:
                    # 根据协议，文本在 result.content[0].text
                    for item in chunk["result"]["content"]:
                        if item["type"] == "text":
                            collected_text.append(item["text"])
            return "\n".join(collected_text)

    async def _post_json(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        assert self.session is not None
        r = await self.session.post(
            self.endpoint, json=payload, headers={"Accept": "application/json"}
        )
        if r.status_code == 204 or not r.content:
            return {}  # ← 通知无响应体
        r.raise_for_status()
        return r.json()

    async def close(self) -> None:
        if self.session:
            await self.session.aclose()
            self.session = None


################################################################################
# LLM 封装（OpenAI Function‑Calling）
################################################################################


class LLMClient:
    def __init__(self, api_key: str, base_url: Optional[str], model: str) -> None:
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def chat(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]]):
        return self.client.chat.completions.create(model=self.model, messages=messages, tools=tools)


################################################################################
# 多服务器 MCP + LLM Function Calling
################################################################################


class MultiHTTPMCPClient:
    def __init__(
        self, servers_conf: Dict[str, Any], api_key: str, base_url: Optional[str], model: str
    ) -> None:
        self.servers: Dict[str, HTTPMCPServer] = {
            name: HTTPMCPServer(name, cfg["endpoint"]) for name, cfg in servers_conf.items()
        }
        self.llm = LLMClient(api_key, base_url, model)
        self.all_tools: List[Dict[str, Any]] = []  # 转为 OAI FC 的 tools 数组

    async def start(self):
        for srv in self.servers.values():
            await srv.initialize()
            tools = await srv.list_tools()
            for t in tools:
                # 重命名以区分不同服务器
                full_name = f"{srv.name}_{t['name']}"
                self.all_tools.append(
                    {
                        "type": "function",
                        "function": {
                            "name": full_name,
                            "description": t["description"],
                            "parameters": t["inputSchema"],
                        },
                    }
                )
        logging.info("已连接服务器并汇总工具：%s", [t["function"]["name"] for t in self.all_tools])

    async def call_local_tool(self, full_name: str, args: Dict[str, Any]) -> str:
        srv_name, tool_name = full_name.split("_", 1)
        srv = self.servers[srv_name]
        # 兼容 city/location
        city = args.get("city") or args.get("location")
        if not city:
            raise ValueError("Missing city/location")
        return await srv.call_tool_stream(tool_name, {"city": city})

    async def chat_loop(self):
        print("🤖 HTTP MCP + Function Calling 客户端已启动，输入 quit 退出")
        messages: List[Dict[str, Any]] = []
        while True:
            user = input("你: ").strip()
            if user.lower() == "quit":
                break
            messages.append({"role": "user", "content": user})
            # 1st LLM call
            resp = self.llm.chat(messages, self.all_tools)
            choice = resp.choices[0]
            if choice.finish_reason == "tool_calls":
                tc = choice.message.tool_calls[0]
                tool_name = tc.function.name
                tool_args = json.loads(tc.function.arguments)
                print(f"[调用工具] {tool_name} → {tool_args}")
                tool_resp = await self.call_local_tool(tool_name, tool_args)
                messages.append(choice.message.model_dump())
                messages.append({"role": "tool", "content": tool_resp, "tool_call_id": tc.id})
                resp2 = self.llm.chat(messages, self.all_tools)
                print("AI:", resp2.choices[0].message.content)
                messages.append(resp2.choices[0].message.model_dump())
            else:
                print("AI:", choice.message.content)
                messages.append(choice.message.model_dump())

    async def close(self):
        for s in self.servers.values():
            await s.close()


################################################################################
# main entry
################################################################################


async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    conf = Configuration()
    servers_conf = conf.load_config("./src/mcp_weather_http/servers_config.json").get(
        "mcpServers", {}
    )
    client = MultiHTTPMCPClient(servers_conf, conf.api_key, conf.base_url, conf.model)
    try:
        await client.start()
        await client.chat_loop()
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
