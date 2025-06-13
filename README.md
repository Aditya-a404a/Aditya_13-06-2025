# Aditya_2025-06-13

## 📌 Project: Store Monitoring System

This project is a backend system that helps Loop monitor the uptime and downtime of restaurant stores in the US based on their business hours and activity logs.

---

## 🧠 Problem Overview

Restaurant stores should ideally stay **active during business hours**. However, due to various reasons, they may go inactive temporarily. The goal is to provide restaurant owners with a report on how often and for how long such downtimes occurred.

---
## 🧾 Data Sources
The system ingests and processes data from three CSVs:
1. **Store Status Logs** (`store_status.csv`)
   - `store_id`, `timestamp_utc`, `status`
   - Periodic status polling in **UTC**
2. **Business Hours** (`business_hours.csv`)
   - `store_id`, `dayOfWeek`, `start_time_local`, `end_time_local`
   - Times are in **local store timezone**
3. **Timezone Info** (`timezones.csv`)
   - `store_id`, `timezone_str`
   - Defaults to `America/Chicago` if missing
---
## 🛠️ Tech Stack
- **Framework**: FastAPI
- **ORM**: SQLModel (built on SQLAlchemy)
- **Database**: PostgreSQL / SQLite (dev)
- **Timezones**: `pytz`, `datetime`
- **UUID**: `uuid4` for report IDs
- **CSV Handling**:`csv` module
---

## 🚀 API Endpoints

### 1. `POST /trigger_report`

- Triggers report generation in the background.
- **Returns**: `{"report_id": "some-uuid-string"}`

### 2. `GET /get_report/{report_id}`

- Checks the status of report generation.
- If not ready:  
  `{"message": "Running"}`
- If ready:  
  Returns the CSV file  with custom header as complete
  
## 📊 Uptime & Downtime Logic

- **Time Conversion**: Converts UTC logs to local time using `timezone_str`
- **Overlap Filtering**: Only calculates uptime/downtime within business hours
- **Interpolation**:
- If two logs exist within business hours, extrapolates between timestamps.
- If only one log exists, assumes status continues till end of interval.
- If no logs, assumes no data and skips that interval.
- Used a simple Step-function
  
## 💡 Ideas for Improvement
- Implement caching to reduce stress on db 
- Add authentication and role-based access.
- Include percent uptime/downtime 
- Add unit + integration tests (e.g., using `pytest` with test DB fixtures).
