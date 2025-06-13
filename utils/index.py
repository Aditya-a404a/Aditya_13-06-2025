
from models.index import Status,Hours,Timezone
from datetime import datetime,timedelta
import aiofiles
import csv
from datetime import datetime,time
from models.index import Status
from sqlalchemy.ext.asyncio import AsyncSession
from db.index import AsyncSessionLocal
from sqlmodel import select
from collections import defaultdict
import pytz
import os
# all the add_xzy function takes data from csv and validate and transform
# using session we just push data in bulk to Database
async def addstatus(f: str, session: AsyncSession):
    async with aiofiles.open(f, mode='r') as f:
        content = await f.read()
    reader = csv.DictReader(content.splitlines())
    data = []
    for row in reader:
        try:
            ts_str = row["timestamp_utc"].rstrip(" UTC")
            ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S.%f")
            data.append(Status(
                store_id=row["store_id"],
                status=row["status"],
                timestamp_utc=ts
            ))
        except Exception as e:
            print(f"Skipping row: {e}")
    session.add_all(data)
    await session.commit()
    
async def addhours(f: str,session : AsyncSession):
    async with aiofiles.open(f, mode='r') as f:
        content = await f.read()
    reader = csv.DictReader(content.splitlines())
    data = []
    seen = set()
    for row in reader:    
        key = (row["store_id"], row["dayOfWeek"])
        if key in seen:
            continue
        try:
            t2 = datetime.strptime(row["start_time_local"], "%H:%M:%S").time()
            t3 = datetime.strptime(row["end_time_local"], "%H:%M:%S").time()
            data.append(Hours(
                    store_id = row["store_id"],
                    dayOfWeek = row["dayOfWeek"],
                    start_time_local = t2,
                    end_time_local = t3
                ))
            seen.add(key)
        except Exception as e:
            print(f"Skipping row due to error: {e}")
    session.add_all(data)
    await session.commit()

async def addtimezone(f: str, session : AsyncSession):
    async with aiofiles.open(f, mode='r') as f:
        content = await f.read()
    reader = csv.DictReader(content.splitlines())
    data = []
    for row in reader:   
        tz = row["timezone_str"] or "America/Chicago"
        data.append(Timezone(store_id=row["store_id"], timezone_str=tz))
    session.add_all(data)
    await session.commit()

# First Function which retrives all the logs of till last week using timedelta and taking max as current 
async def getLogs() -> dict :
    async with AsyncSessionLocal() as session:
        current =  await session.execute(select(Status.timestamp_utc).order_by(Status.timestamp_utc.desc()).limit(1))
        current  = current.first()
        current = current[0] 
        if not current:
            return {}
        cutoff = current - timedelta(days=7)
        result = await session.execute(select(Status).where(Status.timestamp_utc >= cutoff).order_by(Status.timestamp_utc.asc()))
        logs = result.scalars().all()
        logs_by_store = defaultdict(list)
        for x in logs:
            logs_by_store[x.store_id].append(x)
    return logs_by_store
# getting working time of the day ( monday to sunday (0,6) for a specfic store)
# this can be improved as well
async def getworkingtime(store_id: str, day: int) -> list:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Hours.start_time_local, Hours.end_time_local)
            .where(Hours.store_id == store_id, Hours.dayOfWeek == day)
        )
        logs = result.all()
        if not logs:
            return ["00:00:00", "23:59:59"]
        return [logs[0][0], logs[0][1]]

# getting timezone for specfic store_id
async def getTimezone(store_id : str) -> str:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Timezone.timezone_str).where(Timezone.store_id == store_id))
    timezone = result.scalar_one_or_none()
    return timezone

# this is the main logic it takes specific store_logs 
# The logic is
# fetch the store logs
# fetch timezone
# convert log into local time zone
# get start and end date ( till last  week )
# fetch business hours on need and cache them
# make segements pair wise to store duration
# use segments to fill tthe required fields accordingly
async def getData(logs: list, store_id: str):
    # timezone string to timezone using pytz 
    tz_str = await getTimezone(store_id) or "UTC"
    local_tz = pytz.timezone(tz_str)

    # changing logs from utc to local 
    records = []
    for row in logs:
        utc_dt = row.timestamp_utc.replace(tzinfo=pytz.utc)
        loc_dt = utc_dt.astimezone(local_tz)
        records.append((loc_dt, row.status))
    
    records.sort(key=lambda x: x[0])

    #  setting current or now in notion doc it said to take as maximum
    now_loc = records[-1][0] if records else datetime.now(local_tz)

    start_date = min((rec[0].date() for rec in records), default=now_loc.date())
    min_allowed = (now_loc - timedelta(days=7)).date()
    if start_date < min_allowed:
        start_date = min_allowed
    end_date = now_loc.date()

    # we can get all the working time together or as we need it , we are doing the later one 
    business_windows = {}
    d = start_date
    while d <= end_date:
        start_str, end_str = await getworkingtime(store_id, d.weekday())
        try:
            start_t = time.fromisoformat(start_str) if isinstance(start_str, str) else start_str
            end_t = time.fromisoformat(end_str) if isinstance(end_str, str) else end_str
        except Exception:
            start_t, end_t = time(0, 0), time(23, 59, 59)
        biz_start = datetime.combine(d, start_t, tzinfo=local_tz)
        biz_end = datetime.combine(d, end_t, tzinfo=local_tz)
        business_windows[d] = (biz_start, biz_end)
        d += timedelta(days=1)

    #  checking if we have even have logs or not and making pairs to fill the step logic 
    # making segments as (start,end,status) so later we can do end-start in required positions
    segments = []
    if records:
        for (t0, s0), (t1, _) in zip(records, records[1:]):
            segments.append((t0, t1, s0))
        segments.append((records[-1][0], now_loc, records[-1][1]))

        # Back-fill from opening on the first record date
        first_ts, first_status = records[0]
        first_date = first_ts.date()
        if first_date not in business_windows:
            # getting workingtime strs and changing it to phrasing it to time 
            start_str, end_str = await getworkingtime(store_id, first_date.weekday())
            try:
                start_t = time.fromisoformat(start_str) if isinstance(start_str, str) else start_str
                end_t = time.fromisoformat(end_str) if isinstance(end_str, str) else end_str
            except Exception:
                start_t, end_t = time(0, 0), time(23, 59, 59)
            biz_start_first = datetime.combine(first_date, start_t, tzinfo=local_tz)
        else:
            biz_start_first, _ = business_windows[first_date]

        if first_ts > biz_start_first:
            segments.insert(0, (biz_start_first, first_ts, first_status))

    # if no logs then marking day as inactive 
    for date, (biz_start, biz_end) in business_windows.items():
        if biz_start > now_loc:
            continue  # skip future windows
        # check if any segment overlaps this business day
        overlaps = any(
            seg_start < biz_end and seg_end > biz_start and seg_start.date() == date
            for seg_start, seg_end, _ in segments
        )
        if not overlaps:
            segments.append((biz_start, biz_end, 'inactive'))

   
    windows = {
        'last_hour': (now_loc - timedelta(hours=1), now_loc),
        'last_day':  (now_loc - timedelta(days=1), now_loc),
        'last_week': (now_loc - timedelta(days=7), now_loc),
    }

    
    metrics = {'store_id': store_id}
    for win in ['last_hour', 'last_day', 'last_week']:
        metrics[f'uptime_{win}'] = 0.0
        metrics[f'downtime_{win}'] = 0.0

    #  making reports 
    for seg_start, seg_end, status in segments:
        for key, (win_start, win_end) in windows.items():
            # clip to report window
            a = max(seg_start, win_start)
            b = min(seg_end, win_end)
            if a >= b:
                continue
            # clip to that day business hours
            biz_start, biz_end = business_windows[a.date()]
            c = max(a, biz_start)
            d = min(b, biz_end)
            if c >= d:
                continue
            # compute duration
            minutes = (d - c).total_seconds() / 60.0
            duration = minutes if key == 'last_hour' else minutes / 60.0
            # add to uptime/downtime
            field = ('uptime_' if status == 'active' else 'downtime_') + key
            metrics[field] += duration
    return metrics

# generating file named {report_id}.csv
def write_report_to_csv(report_data: list[dict], filename="report.csv"):
    if not report_data:
        return
    fieldnames = list(report_data[0].keys())
    file_exists = os.path.isfile(filename)
    with open(filename, mode="a", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        for row in report_data:
            writer.writerow(row)



