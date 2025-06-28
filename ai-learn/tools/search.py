import json
from serpapi import GoogleSearch
from tools.console import Console


class SearchTool:
    def __init__(self, api_key: str):
        self.api_key = api_key
        if not self.api_key:
            raise ValueError("未设置SERPAPI_KEY环境变量")

    def _parse_results(self, data: dict, count: int) -> list[dict]:
        results = []
        if "organic_results" in data:
            for item in data["organic_results"]:
                results.append(
                    {
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "snippet": item.get("snippet", ""),
                    }
                )
        return results[:count]

    def search(self, query: str, num_results: int = 10) -> list[dict]:
        """执行搜索并返回结构化结果"""
        try:
            params = {
                "q": query,
                "engine": "google",
                "api_key": self.api_key,
                "num": num_results,
                "hl": "zh-CN",
                "gl": "cn",
            }

            Console.log(params)

            res = GoogleSearch(params)
            results = res.get_dict()

            return self._parse_results(results, num_results)

        except Exception as e:
            print(f"搜索失败：{str(e)}")
            return []
