import os
from dotenv import load_dotenv
from function_calling import ChatBot

load_dotenv()


def test_function_calling():
    api_key = str(os.getenv("DEEPSEEK_API_KEY"))
    base_url = str(os.getenv("DEEPSEEK_BASE_URL"))
    model_name = "deepseek-chat"  # 模型名称

    user_message = "北京的天气怎么样？"  # 输入
    chatbot = ChatBot(model_name, base_url, api_key)
    chatbot.chat(user_message)


if __name__ == "__main__":
    test_function_calling()
