from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import google_search

import os
from dotenv import load_dotenv

from tools.file import write_file
from tools.weather import get_weather

load_dotenv(override=True)

# 设置代理
os.environ["HTTP_PROXY"] = "http://127.0.0.1:10080"
os.environ["HTTPS_PROXY"] = "http://127.0.0.1:10080"

# 设置Gemini-API-KEY
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")


model = LiteLlm(
    api_key=os.getenv("OPENAI_API_KEY"),
    model=os.getenv("OPENAI_MODEL"),
)

root_agent = Agent(
    name="simple_agent",
    model=model,
    description="用于进行天气查询和记录的智能体",
    instruction="你是一个乐于助人的助手。"
    "当用户询问特定城市的天气时，"
    "使用 'get_weather' 工具查找相关信息。"
    "当用户询需要将一些信息记录到本地的时候，"
    "使用 'write_file' 将指定内容记录到本地"
    "如果工具返回错误，礼貌地告知用户。",
    tools=[get_weather, write_file, google_search],
)
