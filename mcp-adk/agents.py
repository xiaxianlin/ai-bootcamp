from google.adk.agents import Agent

from tools.file import write_file
from tools.weather import get_weather


def get_simple_agent(model):
    return Agent(
        name="simple_agent",
        model=model,
        instruction="你是一个乐于助人的中文助手。",
        description="回答用户的问题。",
    )


def get_weather_agent(model):
    return Agent(
        name="weather_agent",
        model=model,
        description="用于进行某地天气查询的Agent智能体",
        instruction="你是一个有帮助的天气助手。"
        "当用户询问特定城市的天气时，"
        "使用 'get_weather' 工具查找相关信息。"
        "如果工具返回错误，礼貌地告知用户。",
        tools=[get_weather],
    )


def get_write_file_agent(model):
    return Agent(
        name="write_file_agent",
        model=model,
        description="用于进行信息记录的智能体",
        instruction="你是一个乐于助人的助手。"
        "当用户询需要将一些信息记录到本地的时候，"
        "使用 'write_file' 将指定内容记录到本地"
        "如果工具返回错误，礼貌地告知用户。",
        tools=[write_file],
    )
