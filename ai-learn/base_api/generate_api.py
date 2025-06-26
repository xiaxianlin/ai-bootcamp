import requests, json

generate_url = "http://127.0.0.1:11434/api/generate"


def call():
    generate_payload = {
        "model": "deepseek-r1",
        "prompt": "请生成一个关于人工智能的简短介绍。",
        "stream": False,
    }
    response_generate = requests.post(generate_url, json=generate_payload)

    if response_generate.status_code == 200:
        generate_response = response_generate.json()
        # print("生成响应：", json.dumps(generate_response, ensure_ascii=False, indent=2))
        print("生成响应：", generate_response["response"])
        print("调用时长：", generate_response["total_duration"] / 10e9, "s")
    else:
        print("生成请求失败", response_generate.status_code, response_generate.text)


def call_stream():
    generate_payload = {
        "model": "deepseek-r1",
        "prompt": "请生成一个关于人工智能的简短介绍。",
        "options": {
            "temperature": 0.6,
        },
    }
    response_generate = requests.post(generate_url, json=generate_payload, stream=True)

    if response_generate.status_code == 200:
        for line in response_generate.iter_lines():
            if line:
                try:
                    response_json = json.loads(line.decode("utf-8"))
                    if "response" in response_json:
                        print(response_json["response"], end="", flush=True)

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


if __name__ == "__main__":
    call_stream()
