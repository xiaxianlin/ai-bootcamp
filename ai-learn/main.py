import os
from dotenv import load_dotenv
from embedding.intent_identify import fast_embedding, test_function_call_data

load_dotenv()

api_key = str(os.getenv("DEEPSEEK_API_KEY"))
base_url = str(os.getenv("DEEPSEEK_BASE_URL"))
serpapi_key = os.getenv("SERPAPI_KEY")


if __name__ == "__main__":
    test_function_call_data()
    # text = "我的储蓄账户是否可以与支付软件直接绑定？"
    # function_call_predict(text)
