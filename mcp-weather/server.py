"""weather_http_server_v8.py – MCP Streamable HTTP (Cherry‑Studio verified)
==========================================================================
• initialize  → protocolVersion + capabilities(streaming + tools.listChanged)
                + friendly instructions
• notifications/initialized → ignored (204)
• tools/list  → single-page tool registry (get_weather)
• tools/call  → execute get_weather, stream JSON (content[])
• GET → 405 (no SSE stream implemented)
"""

from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any, AsyncIterator

import httpx
from fastapi import FastAPI, Request, Response, status
from fastapi.responses import StreamingResponse

# ---------------------------------------------------------------------------
# Server constants
# ---------------------------------------------------------------------------
SERVER_NAME = "WeatherServer"
SERVER_VERSION = "1.0.0"
PROTOCOL_VERSION = "2024-11-05"  # Cherry Studio current

# ---------------------------------------------------------------------------
# Weather helpers
# ---------------------------------------------------------------------------
OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
API_KEY: str | None = None
USER_AGENT = "weather-app/1.0"


async def fetch_weather(city: str) -> dict[str, Any]:
    if not API_KEY:
        return {"error": "API_KEY 未设置，请提供有效的 OpenWeather API Key。"}
    params = {"q": city, "appid": API_KEY, "units": "metric", "lang": "zh_cn"}
    headers = {"User-Agent": USER_AGENT}
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            r = await client.get(OPENWEATHER_URL, params=params, headers=headers)
            r.raise_for_status()
            return r.json()
        except httpx.HTTPStatusError as exc:
            return {"error": f"HTTP 错误: {exc.response.status_code}"}
        except Exception as exc:  # noqa: BLE001
            return {"error": f"请求失败: {exc}"}


def format_weather(data: dict[str, Any]) -> str:
    if "error" in data:
        return data["error"]
    city = data.get("name", "未知")
    country = data.get("sys", {}).get("country", "未知")
    temp = data.get("main", {}).get("temp", "N/A")
    humidity = data.get("main", {}).get("humidity", "N/A")
    wind = data.get("wind", {}).get("speed", "N/A")
    desc = data.get("weather", [{}])[0].get("description", "未知")
    return (
        f"🌍 {city}, {country}\n"
        f"🌡 温度: {temp}°C\n"
        f"💧 湿度: {humidity}%\n"
        f"🌬 风速: {wind} m/s\n"
        f"🌤 天气: {desc}"
    )


async def stream_weather(city: str, req_id: int | str) -> AsyncIterator[bytes]:
    # progress chunk
    yield json.dumps(
        {"jsonrpc": "2.0", "id": req_id, "stream": f"查询 {city} 天气中…"}
    ).encode() + b"\n"

    await asyncio.sleep(0.3)
    data = await fetch_weather(city)

    if "error" in data:
        yield json.dumps(
            {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32000, "message": data["error"]}}
        ).encode() + b"\n"
        return

    yield json.dumps(
        {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [{"type": "text", "text": format_weather(data)}],
                "isError": False,
            },
        }
    ).encode() + b"\n"


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="WeatherServer HTTP-Stream v8")

TOOLS_REGISTRY = {
    "tools": [
        {
            "name": "get_weather",
            "description": "用于进行天气信息查询的函数，输入城市英文名称，即可获得当前城市天气信息。",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name, e.g. 'Hangzhou'"}
                },
                "required": ["city"],
            },
        }
    ],
    "nextCursor": None,
}


@app.get("/mcp")
async def mcp_initialize_via_get():
    #  GET 请求也执行了 initialize 方法
    return {
        "jsonrpc": "2.0",
        "id": 0,
        "result": {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"streaming": True, "tools": {"listChanged": True}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            "instructions": "Use the get_weather tool to fetch weather by city name.",
        },
    }


@app.post("/mcp")
async def mcp_endpoint(request: Request):
    try:
        body = await request.json()
        # ✅ 打印客户端请求内容
        print("💡 收到请求:", json.dumps(body, ensure_ascii=False, indent=2))
    except Exception:
        return {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}

    req_id = body.get("id", 1)
    method = body.get("method")

    # ✅ 打印当前方法类型
    print(f"🔧 方法: {method}")

    # 0) Ignore initialized notification (no response required)
    if method == "notifications/initialized":
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    # 1) Activation probe (no method)
    if method is None:
        return {"jsonrpc": "2.0", "id": req_id, "result": {"status": "MCP server online."}}

    # 2) initialize
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"streaming": True, "tools": {"listChanged": True}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                "instructions": "Use the get_weather tool to fetch weather by city name.",
            },
        }

    # 3) tools/list
    if method == "tools/list":
        print(json.dumps(TOOLS_REGISTRY, indent=2, ensure_ascii=False))
        return {"jsonrpc": "2.0", "id": req_id, "result": TOOLS_REGISTRY}

    # 4) tools/call
    if method == "tools/call":
        params = body.get("params", {})
        tool_name = params.get("name")
        args = params.get("arguments", {})

        if tool_name != "get_weather":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32602, "message": "Unknown tool"},
            }

        city = args.get("city")
        if not city:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32602, "message": "Missing city"},
            }

        return StreamingResponse(stream_weather(city, req_id), media_type="application/json")

    # 5) unknown method
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": "Method not found"},
    }


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Weather MCP HTTP-Stream v8")
    parser.add_argument("--api_key", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5005)
    args = parser.parse_args()

    global API_KEY
    API_KEY = args.api_key

    import uvicorn

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
