from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from db.index import AsyncSessionLocal
from utils.index import addhours,addstatus,addtimezone,getLogs,getData,write_report_to_csv
import asyncio
from collections import defaultdict
import uuid

app = FastAPI()
state = defaultdict(lambda : "TRIGGER")


# used to create tables intially 
# @app.on_event("startup")
# async def d():
#     await init_db()

# do not hit this end point after inserting data into db
# @app.get("/loading")
# async def load_csvs():
#     async def load_all():
#         async with AsyncSessionLocal() as session:
#             await addstatus("./store_status.csv", session)
#             await addhours("./menu_hours.csv", session)
#             await addtimezone("./timezones.csv", session)
#     #  passing it to async io  
#     asyncio.create_task(load_all())  # background
#     return {"message": "CSV loading started in background"}

# starts the process of making report 
@app.get("/trigger_report")
async def reportCreation():
    report_id = str(uuid.uuid4())
    state[report_id] = "Running"
    async def process(report_id : str):
        logs = await getLogs()
        data = [] 
        for x in logs.keys():
            data.append(await getData(logs[x],x))
        write_report_to_csv(data,filename=report_id+".csv")
        state[report_id] = "Completed"
    asyncio.create_task(process(report_id))  # background
    return {"message" : report_id}


# tells about the status and returns the file if done 
@app.get("/get_report/{report_id}") 
async def getreportstatus(report_id: str):
    result = state[report_id]
    if result =="TRIGGER":
        return {"message": "NO REPORT OF THIS ID IS FOUND"}
    elif result == "Running":
        return {"message": "Wait"}
    else:
        file_like = open(report_id+".csv", mode="rb")
        headers = {
            "Content-Disposition": f"attachment; filename=report_{report_id}.csv",
            "X-Report-Status": "Complete"  # Custom header
        }
        return StreamingResponse(file_like, media_type="text/csv", headers=headers)










