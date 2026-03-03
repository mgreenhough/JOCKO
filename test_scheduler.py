import asyncio
import sys
sys.path.insert(0, '.')
import database
database.init_db()
from scheduler import send_weekly_report

async def test():
    print("Testing scheduler...")
    await send_weekly_report()
    print("Test complete!")

if __name__ == "__main__":
    asyncio.run(test())
