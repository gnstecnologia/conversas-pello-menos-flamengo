# -*- coding: utf-8 -*-
import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.stdout.reconfigure(encoding="utf-8")
OUT = Path(r"c:\Users\GC1\Desktop\Automação GHL\gamma-vet")
vals = {}
for line in Path(r"c:\Users\GC1\Desktop\Automação GHL\.env").read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()
TOKEN = vals["GHL_GAMMA_API_KEY"]
LOC = vals["GHL_GAMMA_LOCATION_ID"]
CAL = json.loads((OUT / "calendar-ids-live.json").read_text(encoding="utf-8"))
UID = CAL["sharedUserFernanda"]
TZ = ZoneInfo("America/Sao_Paulo")


def curl(method, url, data=None, ver="2021-04-15"):
    cmd = [
        "curl.exe", "-s", "-w", "\nHTTP:%{http_code}",
        "-X", method, url,
        "-H", f"Authorization: Bearer {TOKEN}",
        "-H", f"Version: {ver}",
        "-H", "Accept: application/json",
        "-H", "User-Agent: Mozilla/5.0",
    ]
    if data is not None:
        tmp = OUT / "audit" / "req-rx-debug.json"
        tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        cmd += ["-H", "Content-Type: application/json", "--data-binary", f"@{tmp}"]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    body = r.stdout
    code = "?"
    if "HTTP:" in body:
        body, code = body.rsplit("HTTP:", 1)
        code = code.strip()
    return code, body


code, body = curl(
    "GET",
    f"https://services.leadconnectorhq.com/calendars/schedules/search?locationId={LOC}&userId={UID}",
)
for s in (json.loads(body).get("schedules") or []):
    print("SCH", s.get("id"), s.get("name"), "cals", s.get("calendarIds"))
    days = []
    for r in s.get("rules") or []:
        if r.get("type") == "wday":
            days.append(f"{r.get('day')}{r.get('intervals')}")
    print("  wdays:", days)

for key in ("rx", "tomo"):
    code, body = curl("GET", f"https://services.leadconnectorhq.com/calendars/{CAL[key]}", ver="2021-07-28")
    c = json.loads(body).get("calendar") or {}
    print(
        key,
        "enableOfficeHours", c.get("enableOfficeHours"),
        "isActive", c.get("isActive"),
        "openDays", [x.get("daysOfTheWeek") for x in (c.get("openHours") or [])],
        "users", [m.get("userId") for m in (c.get("teamMembers") or [])],
    )

# try enableOfficeHours true on RX
code, body = curl("GET", f"https://services.leadconnectorhq.com/calendars/{CAL['rx']}", ver="2021-07-28")
cal = json.loads(body).get("calendar") or {}
payload = {
    "name": cal.get("name"),
    "enableOfficeHours": True,
    "slotDuration": 30,
    "slotDurationUnit": "mins",
    "slotInterval": 30,
    "slotIntervalUnit": "mins",
    "openHours": cal.get("openHours"),
    "teamMembers": cal.get("teamMembers"),
}
code, body = curl("PUT", f"https://services.leadconnectorhq.com/calendars/{CAL['rx']}", payload, ver="2021-07-28")
print("RX enableOfficeHours PUT", code, body[:200].replace("\n", " "))

# Also update Work Hours to include sat and associate RX
wh = "qFMZOj1GjAfLRsORSMj7"
payload_wh = {
    "name": "Work Hours",
    "timezone": "America/Sao_Paulo",
    "rules": [
        {"type": "wday", "day": "monday", "intervals": [{"from": "08:00", "to": "18:00"}]},
        {"type": "wday", "day": "tuesday", "intervals": [{"from": "08:00", "to": "18:00"}]},
        {"type": "wday", "day": "wednesday", "intervals": [{"from": "08:00", "to": "18:00"}]},
        {"type": "wday", "day": "thursday", "intervals": [{"from": "08:00", "to": "18:00"}]},
        {"type": "wday", "day": "friday", "intervals": [{"from": "08:00", "to": "18:00"}]},
        {"type": "wday", "day": "saturday", "intervals": [{"from": "08:00", "to": "13:00"}]},
    ],
}
code, body = curl("PUT", f"https://services.leadconnectorhq.com/calendars/schedules/{wh}", payload_wh)
print("Work Hours PUT", code)
for cid, label in ((CAL["rx"], "rx"), (CAL["tomo"], "tomo")):
    code, body = curl("PUT", f"https://services.leadconnectorhq.com/calendars/schedules/{wh}/associations/{cid}")
    print("assoc WH", label, code)

# also new schedule
sid = CAL.get("rxTomoSaturdayScheduleId") or "efEeCk3RDwYXUodB5TPy"
for cid, label in ((CAL["rx"], "rx"), (CAL["tomo"], "tomo")):
    code, body = curl("PUT", f"https://services.leadconnectorhq.com/calendars/schedules/{sid}/associations/{cid}")
    print("assoc NEW", label, code)

now = datetime.now(TZ).replace(hour=0, minute=0, second=0, microsecond=0)
s = int(now.timestamp() * 1000)
e = int((now + timedelta(days=16)).timestamp() * 1000)
for key in ("rx", "tomo"):
    code, body = curl(
        "GET",
        f"https://services.leadconnectorhq.com/calendars/{CAL[key]}/free-slots?startDate={s}&endDate={e}",
        ver="2021-07-28",
    )
    data = json.loads(body) if body.strip().startswith("{") else {}
    print("==", key)
    for k, v in sorted(data.items()):
        if k == "traceId" or not isinstance(v, dict):
            continue
        wd = datetime.fromisoformat(k).weekday()
        n = len(v.get("slots") or [])
        if wd == 5 or n:
            print(" ", k, "wd", wd, "n", n)
