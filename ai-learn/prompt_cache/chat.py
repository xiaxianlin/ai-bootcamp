import os, time, hashlib, requests, json
import numpy as np
from redis import Redis
from openai import OpenAI
from dotenv import load_dotenv


load_dotenv()


class OllamaEmbedding:
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "bge-m3"):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_url = f"{self.base_url}/api/embed"

    def embed_query(self, text: str) -> list[float]:
        payload = {
            "model": self.model,
            "input": text,
        }
        try:
            response = requests.post(self.api_url, json=payload)
            response.raise_for_status()
            result = response.json()
            return result["embeddings"][0]
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return []

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        payload = {
            "model": self.model,
            "input": texts,
        }
        try:
            response = requests.post(self.api_url, json=payload)
            response.raise_for_status()
            result = response.json()
            return result["embeddings"]
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return []


class RedisSemanticCache:
    def __init__(self, embeding_model, prefix: str = "cache:"):
        self.client = Redis(host="127.0.0.1", port=6379, db=0)
        self.embedding = embeding_model
        self.prefix = prefix

    def _create_key(self, text: str) -> str:
        md5_hash = hashlib.md5(text.encode("utf-8")).hexdigest()
        return f"{self.prefix}{md5_hash}"

    def add_text(self, text: str, metadata: dict = None):
        vector = self.embedding.embed_query(text)
        key = self._create_key(text)

        data = {
            "text": text,
            "vector": str(vector),
            "metadata": str(metadata or {}),
        }

        self.client.hset(key, mapping=data)

    def get_text(self, key: str) -> dict:
        return self.client.hgetall(key)

    def list_all_keys(self):
        pattern = f"{self.prefix}*"
        return [key.decode() for key in self.client.keys(pattern)]

    def get_by_text(self, text: str):
        key = self._create_key(text)
        result = self.client.hgetall(key)
        if result:
            return {k.decode(): v.decode() for k, v in result.items()}
        return None

    def get_all_text(self):
        all_data = []
        for key in self.list_all_keys():
            data = self.client.hgetall(key)
            if data:
                all_data.append({key.decode(): v.decode for k, v in data.items()})

    def clear_all_cache(self):
        pattern = f"{self.prefix}"
        keys = self.client.keys(pattern)
        if keys:
            self.client.delete(*keys)
            print(f"已清除 {len(keys)} 条缓存")
        else:
            print("缓存为空")


class SemanticCache(RedisSemanticCache):
    def calculate_similarity(self, vec1, vec2) -> float:
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

    def similarity_search(self, query: str, threshold: float = 0.8) -> list[dict]:
        query_vector = self.embedding.embed_query(query)
        results = []
        for key in self.client.keys(f"{self.prefix}*"):
            cached_data = self.get_text(key)
            if not cached_data:
                continue

            cached_vector = eval(cached_data[b"vector"])
            similarity = self.calculate_similarity(query_vector, cached_vector)

            if similarity >= threshold:
                results.append(
                    {
                        "text": cached_data[b"text"].decode(),
                        "similarity": similarity,
                    }
                )
        return sorted(results, key=lambda x: x["similarity"], reverse=True)


class OllamaChat:
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "deepseek-r1"):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.chat_api = f"{self.base_url}/api/chat"
        self.embedding = OllamaEmbedding()
        self.cache = RedisSemanticCache(embeding_model=self.embedding)

    def _calculate_similarity(self, vec1, vec2) -> float:
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

    def _get_llm_answer(self, question: str) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": question}],
            "stream": False,
            "options": {
                "temperature": 1.3,
            },
        }
        try:
            response = requests.post(self.chat_api, json=payload)
            response.raise_for_status()
            result = response.json()
            return result["message"]["content"]
        except Exception as e:
            print(f"Error getting answer: {e}")
            return ""

    def get_answer_with_cache(self, question: str, similarity_threshold: float = 0.9):
        query_vector = self.embedding.embed_query(question)

        max_similarity = 0
        cached_answer = None

        for key in self.cache.list_all_keys():
            data = self.cache.client.hgetall(key)
            if not data:
                continue

            cached_vector = eval(data[b"vector"])
            similarity = self._calculate_similarity(query_vector, cached_vector)
            print(f"similarity: {similarity}")
            if similarity > max_similarity:
                max_similarity = similarity
                if similarity >= similarity_threshold:
                    metadata = eval(data[b"metadata"].decode())
                    cached_answer = {
                        "answer": metadata["answer"],
                        "source": "cache",
                        "similarity": similarity,
                        "original_question": data[b"text"].decode(),
                    }

        if cached_answer:
            return cached_answer

        answer = self._get_llm_answer(question)

        self.cache.add_text(
            text=question,
            metadata={
                "answer": answer,
                "source": "llm",
            },
        )

        return {
            "answer": answer,
            "source": "llm",
            "similarity": 0,
            "original_question": None,
        }


if __name__ == "__main__":
    chat_model = OllamaChat()
    question = "人工智能是什么"
    result = chat_model.get_answer_with_cache(question)
    print(f"问题： {question}")
    print(f"来源： {result['source']}")
    print(f"答案： {result['answer']}")
