import os
import asyncio
from openai import AsyncOpenAI
from mcp.server.fastmcp import FastMCP
from agents import Runner, set_default_openai_client, set_tracing_disabled
from services import WebSearchPlan, ReportData, planner_agent, search_agent, writer_agent

mcp = FastMCP("DeepResearch")
USER_AGENT = "deepresearch-app/1.0"


async def _plan_searches(query: str) -> WebSearchPlan:
    """
    用于进行某个搜索主题的搜索规划
    """
    result = await Runner.run(
        planner_agent,
        f"Query: {query}",
    )
    return result.final_output_as(WebSearchPlan)


async def _perform_searches(search_plan: WebSearchPlan) -> list[str]:
    """
    用于实际执行搜索，并组成搜索条目列表
    """
    tasks = [asyncio.create_task(_search(item)) for item in search_plan.searches]
    results = []
    for task in asyncio.as_completed(tasks):
        result = await task
        if result is not None:
            results.append(result)
    return results


async def _search(item: WebSearchPlan) -> str | None:
    """
    实际负责进行搜索，并完成每个搜索条目的短文本编写
    """
    try:
        result = await Runner.run(
            search_agent, input=f"Search term: {item.query}\nReason for searching: {item.reason}"
        )
        return str(result.final_output)
    except Exception:
        return None


async def _write_report(query: str, search_results: list[str]) -> ReportData:
    """
    根据搜索的段文档，编写长文本
    """
    result = await Runner.run(
        writer_agent,
        input=f"Original query: {query}\nSummarized search results: {search_results}",
    )
    return result.final_output_as(ReportData)


@mcp.tool()
async def deepresearch(query: str) -> ReportData:
    """
    主函数，输入一个研究主题，自动完成搜索规划、搜索、写报告。
    返回最终的 ReportData 对象，就是一个markdown格式的完整的研究报告文档
    """
    search_plan = await _plan_searches(query)
    search_results = await _perform_searches(search_plan)
    report = await _write_report(query, search_results)
    return report


def main():
    # 初始化 external_client 和设置
    external_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    set_default_openai_client(external_client)
    set_tracing_disabled(True)

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
