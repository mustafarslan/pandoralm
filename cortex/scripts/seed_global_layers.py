
import asyncio
import os
import sys

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import async_session_factory
from app.models.layer import Layer, LayerType, QuotaTier

SYSTEM_ID = 'a0000000-0000-0000-0000-000000000001'
ORG_ID = 'a0000000-0000-0000-0000-000000000002'
ENG_ID = 'a0000000-0000-0000-0000-000000000003'

async def seed():
    print("Connecting to database...")
    async with async_session_factory() as session:
        print("Checking Global Layers...")
        
        # Check and Insert Organization
        org = await session.get(Layer, ORG_ID)
        if not org:
            print(f"Seeding Organization Layer ({ORG_ID})...")
            session.add(Layer(
                id=ORG_ID,
                name="Global Organization",
                type=LayerType.ORGANIZATION,
                color="violet",
                is_global=True,
                quota_tier=QuotaTier.ENTERPRISE,
                storage_quota_bytes=1099511627776 # 1TB
            ))
        else:
            print("Organization Layer exists.")
        
        # Check and Insert Engineering
        eng = await session.get(Layer, ENG_ID)
        if not eng:
             print(f"Seeding Engineering Layer ({ENG_ID})...")
             session.add(Layer(
                 id=ENG_ID,
                 name="Global Engineering",
                 type=LayerType.TEAM,
                 color="blue",
                 is_global=True,
                 quota_tier=QuotaTier.ENTERPRISE,
                 storage_quota_bytes=1099511627776 # 1TB
             ))
        else:
            print("Engineering Layer exists.")
        
        await session.commit()
        print("Seeding completed successfully.")

if __name__ == "__main__":
    asyncio.run(seed())
