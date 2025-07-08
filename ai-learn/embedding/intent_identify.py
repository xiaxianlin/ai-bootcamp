import pandas as pd
import numpy as np
import os
import openai
import dotenv
import time
from embedding.tools import *
from openai import OpenAI
import tiktoken


dotenv.load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def num_tokens_from_string(string: str, encoding_name: str) -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens


def tiktoken_embedding(text):
    encoding = tiktoken.encoding_for_model("gpt-4o")
    data = encoding.encode(text)
    print(f"[EMBEDDING] => {text} => {data}")
    return data


def openai_embedding(text):
    res = client.embeddings.create(
        input=text,
        model="text-embedding-3-small",
        encoding_format="float",
    )
    data = res.data[0].embedding
    print(f"[EMBEDDING] => {text} => {data}")
    return data


def embedding_data():
    train_df = pd.read_csv("data/train_dataset.csv")
    test_df = pd.read_csv("data/test_dataset.csv")

    pd.set_option("display.max_rows", None)

    print("开始 Embeding...")
    now = time.time()
    train_df["embedding"] = train_df.Conversation.apply(lambda x: openai_embedding(x))
    end = time.time()
    print(f"用时：{end-now} 秒")
    print(train_df.head())
    train_df.to_csv("data/embedding_train_dataset.csv")

    print("开始 Embeding...")
    now = time.time()
    test_df["embedding"] = train_df.Conversation.apply(lambda x: openai_embedding(x))
    end = time.time()
    print(f"用时：{end-now} 秒")
    print(test_df.head())
    test_df.to_csv("data/embedding_test_dataset.csv")


def function_call_predict(text):
    # 创建message
    messages = [
        {
            "role": "system",
            "content": "你是一个智能银行客户接待应用，输入的每个user message都是某位银行客户的需求。\
        你的每一次回答都必须调用function call来完成。请仔细甄别用户需求，并合理调用外部函数来进行回答。",
        },
        {"role": "user", "content": text},
    ]

    # 创建回答
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        functions=functions,
        function_call="auto",
    )
    response_message = response.choices[0].message

    # 获取分类结果
    res = 0
    if response_message.function_call:
        function_name = response_message.function_call.name
        res = type_dict[function_name]

    print(f"[EMBEDDING] => {text} => {res}")

    return res


def embedding_function_call_data():
    train_df = pd.read_csv("data/embedding_train_dataset.csv")
    test_df = pd.read_csv("data/embedding_test_dataset.csv")

    pd.set_option("display.max_rows", None)

    print("开始 Embeding...")
    now = time.time()
    train_df["function_call_prediction_3.5"] = train_df.Conversation.apply(
        lambda x: function_call_predict(x)
    )
    end = time.time()
    print(f"用时：{end-now} 秒")
    print(train_df.head())
    train_df.to_csv("data/func_embedding_train_dataset.csv")

    print("开始 Embeding...")
    now = time.time()
    test_df["function_call_prediction_3.5"] = test_df.Conversation.apply(
        lambda x: function_call_predict(x)
    )
    end = time.time()
    print(f"用时：{end-now} 秒")
    print(test_df.head())
    test_df.to_csv("data/func_embedding_test_dataset.csv")


def fast_embedding():
    test_df = pd.read_csv("data/embedding_test_dataset.csv")
    for index, row in enumerate(test_df.itertuples()):
        try:
            # 尝试执行 function_call_predict 函数
            test_df.at[index, "function_call_prediction_3.5"] = function_call_predict(
                row.Conversation
            )
        except Exception as e:
            # 打印错误信息并等待一分钟
            print(f"Error on row {index}: {e}")
            time.sleep(60)  # 等待一分钟
            continue  # 继续下一次循环
        # 每10行打印一次进度
        if index % 10 == 0:
            print(f"Processed {index}/{len(test_df)} rows")

    test_df.to_csv("data/func_embedding_test_dataset.csv")


def test_function_call_data():
    train_df = pd.read_csv("data/func_embedding_train_dataset.csv")
    test_df = pd.read_csv("data/func_embedding_test_dataset.csv")
    print("查看训练数据误判样例：")
    train_df = train_df[["Conversation", "type", "function_call_prediction_3.5"]]
    print(train_df[train_df["function_call_prediction_3.5"] != train_df["type"]])
    print("查看测试数据误判样例：")
    test_df = test_df[["Conversation", "type", "function_call_prediction_3.5"]]
    print(test_df[test_df["function_call_prediction_3.5"] != test_df["type"]])


if __name__ == "__main__":
    embedding_data()
