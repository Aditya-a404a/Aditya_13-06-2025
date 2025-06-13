from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

#  Should be in env Just for development sake written directly here
# password is removed
DATABASE_URL = "mysql+aiomysql://root:@localhost:3306/loopdata"

# Using Async engine 
engine = create_async_engine(DATABASE_URL)
# using AsyncSessionLocal to create Session for different Transactions
AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
