import os
from dotenv import load_dotenv
from function_calling import ChatBot
from web_search import SearchBot

load_dotenv()

api_key = str(os.getenv("DEEPSEEK_API_KEY"))
base_url = str(os.getenv("DEEPSEEK_BASE_URL"))
serpapi_key = os.getenv("SERPAPI_KEY")


def test_function_calling():
    user_message = "你好，请介绍一下你自己"  # 输入
    chatbot = ChatBot("deepseek-chat", base_url, api_key)
    chatbot.chat(user_message)


def test_web_search():
    bot = SearchBot("deepseek-chat", base_url, api_key, serpapi_key)
    bot.chat("今天的世界主要股指是多少")


if __name__ == "__main__":
    test_web_search()
