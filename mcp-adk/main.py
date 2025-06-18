import os
import asyncio
from dotenv import load_dotenv
from google.adk.models.lite_llm import LiteLlm
from google.adk.sessions import DatabaseSessionService
from google.adk.runners import Runner
from google.genai import types

from agents import get_weather_agent

load_dotenv()

APP_NAME = "test_app"
USER_ID = "user_1"
SESSION_ID = "session_001"

model = LiteLlm(api_key=os.getenv("OPENAI_API_KEY"), model=os.getenv("OPENAI_MODEL"))


def create_session_service():
    # session_service = InMemorySessionService()
    return DatabaseSessionService(db_url=os.getenv("MYSQL_URL"))


async def create_session(service: DatabaseSessionService):
    return await service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID,
    )


async def get_seesion(service: DatabaseSessionService):
    return await service.get_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID,
    )


def create_runner(session_service, agent):
    runner = Runner(
        agent=agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

    return runner


async def call_agent_async(*, query: str, runner: Runner, user_id, session_id):
    content = types.Content(role="user", parts=[types.Part(text=query)])
    final_response_text = "Agent did not produce a final response."
    events = runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=content,
    )
    async for event in events:

        if event.is_final_response():
            if event.content and event.content.parts:
                final_response_text = event.content.parts[0].text
            elif event.actions and event.actions.escalate:
                final_response_text = f"Error: {event.error_message or 'No specific message.'}"
            break

    return final_response_text


async def main():
    service = create_session_service()
    session = await get_seesion(service)
    if not session:
        session = await create_session(service)

    print(f"app_name: {session.app_name}")
    print(f"user_id: {session.user_id}")
    print(f"session_id: {session.id}")

    runner = create_runner(service, get_weather_agent(model))
    print(f"Runner created for agent '{runner.agent.name}'.")

    """运行交互式聊天循环"""
    print("\nMCP 客户端已启动！输入 'quit' 退出")

    while True:
        query = input("\n你: ").strip()
        if query.lower() == "quit":
            break
        try:
            result = await call_agent_async(
                query=query,
                runner=runner,
                user_id=session.user_id,
                session_id=session.id,
            )
            print(f"\n🤖: {result}")
        except Exception as e:
            print(f"\n⚠️ 发生错误: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())
