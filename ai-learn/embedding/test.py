from ast import literal_eval
from pprint import pprint
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import classification_report, mean_absolute_error, mean_squared_error
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
import tiktoken

import os
import openai
import dotenv

dotenv.load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")


def get_embedding(text, model="text-embedding-3-small"):
    pprint(f"[EMBEDDING] => {text}")
    try:
        response = openai.embeddings.create(input=text, model=model)
        return response.data[0].embedding
    except Exception as e:
        print(f"Error on attempt: {e}")


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def label_score(review_embedding, label_embeddings):
    # 计算给定评论Embedding与正面标签Embedding的余弦相似度与其与负面标签Embedding的余弦相似度之差
    return cosine_similarity(review_embedding, label_embeddings[1]) - cosine_similarity(
        review_embedding, label_embeddings[0]
    )


def handleData():
    df = pd.read_csv("Reviews.csv", index_col=0)
    df = df[["ProductId", "UserId", "Score", "Summary", "Text"]]
    df = df.dropna()
    df["combined"] = (
        "Title: " + df.Summary.str.strip() + "; Content: " + df.Text.str.strip()  # 合并字段
    )
    print(df.head(5))
    embedding_encoding = "cl100k_base"
    max_tokens = 8000
    top_n = 1000
    encoding = tiktoken.get_encoding(embedding_encoding)
    df["n_tokens"] = df.combined.apply(lambda x: len(encoding.encode(x)))
    df = df[df.n_tokens <= max_tokens].tail(top_n)
    df["embedding"] = df.combined.apply(lambda x: get_embedding(x))
    print(df.head(5))
    df.to_csv("embedding_reviews.csv")


# 定义零样本分类的评估函数
def evaluate_embeddings_approach(df, labels=["negative", "positive"]):
    # 获取标签的Embedding
    label_embeddings = [get_embedding(label) for label in labels]

    # 定义标签评分函数

    # 计算每个评论的评分
    probas = df["embedding"].apply(lambda x: label_score(x, label_embeddings))
    # 基于评分做出最终的预测情感
    preds = probas.apply(lambda x: "positive" if x > 0 else "negative")


def zsl():
    df = pd.read_csv("embedding_reviews.csv")
    df["embedding"] = df.embedding.apply(literal_eval).apply(np.array)
    df = df[df.Score != 3]
    df["sentiment"] = df.Score.replace({1: "negative", 2: "negative", 4: "positive", 5: "positive"})

    label_embeddings = [get_embedding(label) for label in ["negative", "positive"]]
    probas = df["embedding"].apply(lambda x: label_score(x, label_embeddings))
    preds = probas.apply(lambda x: "positive" if x > 0 else "negative")
    # 打印分类报告
    report = classification_report(df.sentiment, preds)
    print(report)


def learn01():
    df = pd.read_csv("embedding_reviews.csv")
    df["embedding"] = df.embedding.apply(literal_eval).apply(np.array)
    # 将数据拆分为训练集和测试集
    X_train, X_test, y_train, y_test = train_test_split(
        list(df.embedding.values), df.Score, test_size=0.2, random_state=42
    )
    rfr = RandomForestRegressor(n_estimators=100)
    rfr.fit(X_train, y_train)
    preds = rfr.predict(X_test)

    mse = mean_squared_error(y_test, preds)
    mae = mean_absolute_error(y_test, preds)

    bmse = mean_squared_error(y_test, np.repeat(y_test.mean(), len(y_test)))
    bmae = mean_absolute_error(y_test, np.repeat(y_test.mean(), len(y_test)))

    print(f"平均预测效果: mse={bmse:.2f}, mae={bmae:.2f}")


def learn02():
    df = pd.read_csv("embedding_reviews.csv")
    df["embedding"] = df.embedding.apply(literal_eval).apply(np.array)
    # 将数据拆分为训练集和测试集
    X_train, X_test, y_train, y_test = train_test_split(
        list(df.embedding.values), df.Score, test_size=0.2, random_state=42
    )
    clf = RandomForestClassifier(n_estimators=100)
    clf.fit(X_train, y_train)
    preds = clf.predict(X_test)
    # probas = clf.predict_proba(X_test)

    report = classification_report(y_test, preds, zero_division=)
    print(report)


if __name__ == "__main__":
    learn02()
