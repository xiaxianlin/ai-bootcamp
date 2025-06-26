import json, requests

chat_url = "http://127.0.0.1:11434/api/chat"
chat_payload = {
    "model": "deepseek-r1",
    "messages": [
        {
            "role": "user",
            "content": "请生成一个关于人工智能的简短介绍。",
        },
    ],
    "tools": [],
    "stream": True,
    "options": {
        "temperature": 0.7,
        "num_ctx": 2048,
        "num_predict": 4096,
    },
}

with requests.post(chat_url, json=chat_payload, stream=True) as response_generate:
    if response_generate.status_code == 200:
        for line in response_generate.iter_lines():
            if line:
                try:
                    response_json = json.loads(line.decode("utf-8"))
                    if "message" in response_json:
                        print(response_json["message"]["content"], end="", flush=True)

                    if response_json.get("done", False):
                        print("\n\n 完整响应：", json.dumps(response_json))
                except json.JSONDecodeError as e:
                    print(f"JSON 解析错误：{e}")

        if response_json["eval_duration"] != 0:
            tokens_per_second = response_json["eval_count"] / response_json["eval_duration"] * 10**9
            print(f"\n\n 每秒 token 数量：{tokens_per_second}")
        else:
            print("\n\n 每秒 token 数无法计算")
    else:
        print("生成请求失败", response_generate.status_code, response_generate.text)
