# -*- coding: utf-8 -*-
import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone

ENV = r"c:\Users\GC1\Desktop\Automação GHL\.env"
vals = {}
with open(ENV, encoding="utf-8") as f:
    for line in f:
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            vals[k.strip()] = v.strip()

KEY = vals["GHL_GAMMA_API_KEY"]
LOC = vals["GHL_GAMMA_LOCATION_ID"]
UID = "LxQOtMzWVhRqNLlWnLCI"
RX = "vg2u63L3YGB06FIYxir7"
UA = "Mozilla/5.0"


def req(method, url, body=None, version="2021-04-15"):
    data = None if body is None else json.dumps(body).encode("utf-8")
    r = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {KEY}",
            "Version": version,
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": UA,
        },
    )
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print("ERR", e.code, e.read().decode("utf-8", errors="replace")[:800])
        return None


sch = req("GET", f"https://services.leadconnectorhq.com/calendars/schedules/search?locationId={LOC}&userId={UID}")
for s in (sch or {}).get("schedules") or []:
    print("schedule", s.get("id"), "calIds", s.get("calendarIds"))
    for r in s.get("rules") or []:
        print(" ", r.get("day"), r.get("intervals"))

cal = req("GET", f"https://services.leadconnectorhq.com/calendars/{RX}")
c = (cal or {}).get("calendar", cal)
print("\nRX enableOfficeHours", c.get("enableOfficeHours"), "isActive", c.get("isActive"))
print("openHours days", [x.get("daysOfTheWeek") for x in (c.get("openHours") or [])])

loc = req("GET", f"https://services.leadconnectorhq.com/locations/{LOC}", version="2021-07-28")
l = (loc or {}).get("location", loc) or {}
print("\nlocation keys with hour", [k for k in l if "hour" in k.lower() or "time" in k.lower() or "avail" in k.lower() or "office" in k.lower()])
for k in ["name", "timezone", "businessHours", "officeHours", "availability", "settings"]:
    if k in l:
        print(k, json.dumps(l[k], ensure_ascii=False)[:500])

# try associate schedule to RX
sid = "qFMZOj1GjAfLRsORSMj7"
print("\nassociate RX")
out = req("PUT", f"https://services.leadconnectorhq.com/calendars/schedules/{sid}/associations/{RX}")
print(out)

tz = timezone(timedelta(hours=-3))
day_s = "2026-08-22"
start = datetime.fromisoformat(f"{day_s}T00:00:00").replace(tzinfo=tz)
s = int(start.timestamp() * 1000)
e = int((start + timedelta(days=1)).timestamp() * 1000)
sl = req(
    "GET",
    f"https://services.leadconnectorhq.com/calendars/{RX}/free-slots?startDate={s}&endDate={e}",
    version="2021-07-28",
)
print("sat slots", len(((sl or {}).get(day_s) or {}).get("slots") or []), sl)
