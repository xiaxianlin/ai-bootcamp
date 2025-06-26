import json
from openai import OpenAI


class ChatBot:
    def __init__(self, model: str, base_url: str, api_key: str):
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.model = model

    # 定义外部工具库
    # 1. 自定义函数
    def get_weather(self, location: str) -> str:
        """获取实时的天气数据，包括天气状况、温度"""
        weather_data = {
            "北京": "晴天，气温 25°C",
            "上海": "多云，气温 22°C",
            "广州": "小雨，气温 28°C",
            "深圳": "阴天，气温 27°C",
        }
        return weather_data.get(location, "城市未找到，无法提供天气信息。")

    def create_tools(self):
        """创建工具定义"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get real-time weather data, including weather conditions, temperatures",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "The city name, e.g. Beijing",
                            }
                        },
                        "required": ["location"],
                    },
                },
            }
        ]

    def chat(self, user_message: str):
        """对话函数"""
        messages = [
            {"role": "system", "content": "你是一个智能助手，能够回答用户的问题并提供帮助。"},
            {"role": "user", "content": user_message},
        ]

        print("用户输入\t:", user_message)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=self.create_tools(),  # 通过tools参数传递工具的 JsonSchema 表示
        )

        finish_reason = response.choices[0].finish_reason

        if finish_reason == "stop":
            # 普通问答处理
            print("模型输出\t:", response.choices[0].message.content)

        elif finish_reason == "tool_calls":
            assistant_message = response.choices[0].message
            print("参数解析\t:", response.choices[0].message.tool_calls[0].function.arguments)

            messages.append(assistant_message)

            tool_calls = assistant_message.tool_calls
            if tool_calls:
                function_name = tool_calls[0].function.name
                function_args = json.loads(tool_calls[0].function.arguments)

                available_functions = {"get_weather": self.get_weather}

                if function_name in available_functions:
                    function_response = available_functions[function_name](**function_args)
                    print(f"执行结果\t: {function_response}")
                    # 添加工具调用的响应到消息中
                    messages.append(
                        {
                            "role": "tool",
                            "content": str(function_response),
                            "tool_call_id": tool_calls[0].id,
                        }
                    )

                    final_response = self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                    )

                    print("最终回复\t:", final_response.choices[0].message.content)
                else:
                    print(f"Function {function_name} is not available.")
            else:
                print("No tool calls returned from model")
        else:
            print("Unknown finish reason:", finish_reason)
