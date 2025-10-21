import asyncio
from dotenv import load_dotenv
load_dotenv()
from browser_use import Agent
from browser_use.llm import ChatGoogle

async def main():
    agent = Agent(
        task="AI automation jobs in accenture germany",
        llm=ChatGoogle(model="gemini-2.0-flash", temperature=1.0),
    )
    await agent.run()

asyncio.run(main())