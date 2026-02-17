"""Clear database script"""
import asyncio
from database.db import init_db, get_session_local
from sqlalchemy import text


async def clear():
    await init_db()
    async with get_session_local() as session:
        await session.execute(text('DELETE FROM validations'))
        await session.commit()
        print('Database cleared')


if __name__ == "__main__":
    asyncio.run(clear())
