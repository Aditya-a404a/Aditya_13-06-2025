from datetime import datetime,time
from sqlmodel import Field, SQLModel, Session, create_engine, select

class Status(SQLModel, table=True):
    #  Primarykey 
    store_id: str = Field(default=None,description="Unique identifier for the store",primary_key=True)
    status: str = Field(index=True,description="Current status of the store ('active', 'inactive')")
    timestamp_utc: datetime = Field(default_factory=datetime.utcnow,description="UTC timestamp when the status was recorded",primary_key = True)

    # def __repr__(self):
    #     return f"<Status(store_id='{self.store_id}', " \
    #            f"status='{self.status}', " \
    #            f"timestamp_utc='{self.timestamp_utc}')>"

class Hours(SQLModel, table=True):
    # PrimaryKey = (store_id,dayOfWeek)
    store_id: str = Field(primary_key=True, index=True)
    dayOfWeek: int = Field(ge=0, le=6, description="Day of the week (0=Monday, 6=Sunday)", primary_key=True)
    start_time_local: time
    end_time_local: time
    # def __repr__(self):
    #     return f"<Hours(store_id='{self.store_id}', " \
    #            f"dayOfWeek='{self.dayOfWeek}', " \
    #            f"start_time_local='{self.dayOfWeek}', " \
    #            f"end_time_local='{self.timestamp_utc}')>"

class Timezone(SQLModel, table=True):
    # PrimaryKey = (store_id,daysOfWeek)
    store_id: str = Field(unique=True, index=True,primary_key=True) 
    timezone_str: str = Field(max_length=60) 