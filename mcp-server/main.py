import os
import asyncio
import nest_asyncio
from dotenv import load_dotenv
from openai import AsyncOpenAI
from agents import set_default_openai_client, set_tracing_disabled
from rich.console import Console
from rich.markdown import Markdown
from server import deepresearch

load_dotenv()
nest_asyncio.apply()

external_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
set_default_openai_client(external_client)
set_tracing_disabled(True)


async def main():
    report = await deepresearch("人工智能在教育领域的应用")
    with open("report.md", "w", encoding="utf-8") as f:
        f.write(report.markdown_report)

    md = Markdown(report.markdown_report)
    console = Console()
    console.print(md)


if __name__ == "__main__":
    asyncio.run(main())
