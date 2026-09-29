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
CAL = json.loads((OUT / "calendar-ids-live.json").read_text(encoding="utf-8"))
UID = CAL["sharedUserFernanda"]
TZ = ZoneInfo("America/Sao_Paulo")


def curl(method, url, data=None):
    cmd = [
        "curl.exe", "-s", "-w", "\nHTTP:%{http_code}",
        "-X", method, url,
        "-H", f"Authorization: Bearer {TOKEN}",
        "-H", "Version: 2021-07-28",
        "-H", "Accept: application/json",
        "-H", "User-Agent: Mozilla/5.0",
    ]
    if data is not None:
        tmp = OUT / "audit" / "req-excel-align.json"
        tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        cmd += ["-H", "Content-Type: application/json", "--data-binary", f"@{tmp}"]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    body = r.stdout
    code = "?"
    if "HTTP:" in body:
        body, code = body.rsplit("HTTP:", 1)
        code = code.strip()
    return code, body


code, body = curl("GET", f"https://services.leadconnectorhq.com/calendars/{CAL['rx']}")
cal = json.loads(body).get("calendar") or {}
print("RX before days", [b.get("daysOfTheWeek") for b in (cal.get("openHours") or [])])

payload = {
    "name": cal.get("name") or "Raio-X",
    "description": cal.get("description") or "",
    "calendarType": cal.get("calendarType") or "service_booking",
    "slotDuration": 30,
    "slotDurationUnit": "mins",
    "slotInterval": 30,
    "slotIntervalUnit": "mins",
    "openHours": [
        {"daysOfTheWeek": [1], "hours": [{"openHour": 8, "openMinute": 30, "closeHour": 18, "closeMinute": 0}]},
        {"daysOfTheWeek": [2], "hours": [{"openHour": 8, "openMinute": 30, "closeHour": 18, "closeMinute": 0}]},
        {"daysOfTheWeek": [3], "hours": [{"openHour": 8, "openMinute": 30, "closeHour": 18, "closeMinute": 0}]},
        {"daysOfTheWeek": [4], "hours": [{"openHour": 8, "openMinute": 30, "closeHour": 18, "closeMinute": 0}]},
        {"daysOfTheWeek": [5], "hours": [{"openHour": 8, "openMinute": 30, "closeHour": 18, "closeMinute": 0}]},
        {"daysOfTheWeek": [6], "hours": [{"openHour": 8, "openMinute": 0, "closeHour": 13, "closeMinute": 0}]},
    ],
    "teamMembers": cal.get("teamMembers")
    or [{"userId": UID, "priority": 0.5, "selected": True, "isPrimary": True}],
}
code, body = curl("PUT", f"https://services.leadconnectorhq.com/calendars/{CAL['rx']}", payload)
print("RX PUT", code, body[:350].replace("\n", " "))

code, body = curl("GET", f"https://services.leadconnectorhq.com/calendars/{CAL['rx']}")
cal = json.loads(body).get("calendar") or {}
print("RX after days", [b.get("daysOfTheWeek") for b in (cal.get("openHours") or [])])

# cintilo GET
code, body = curl("GET", f"https://services.leadconnectorhq.com/calendars/{CAL['cintilo']}")
c = json.loads(body).get("calendar") or {}
print("cintilo desc", (c.get("description") or "")[:120])
print("cintilo openHours", json.dumps(c.get("openHours"), ensure_ascii=False)[:500])

now = datetime.now(TZ).replace(hour=0, minute=0, second=0, microsecond=0)
s = int(now.timestamp() * 1000)
e = int((now + timedelta(days=12)).timestamp() * 1000)
for key in ("cintilo", "rx"):
    url = (
        f"https://services.leadconnectorhq.com/calendars/{CAL[key]}/free-slots"
        f"?startDate={s}&endDate={e}"
    )
    code, body = curl("GET", url)
    data = json.loads(body) if body.strip().startswith("{") else {}
    print("==", key, code)
    for k, v in sorted(data.items()):
        if not isinstance(v, list):
            continue
        times = []
        for item in v:
            if isinstance(item, str) and "T" in item:
                dt = datetime.fromisoformat(item.replace("Z", "+00:00")).astimezone(TZ)
                times.append(dt.strftime("%Y-%m-%d %a %H:%M"))
        if times:
            print(" ", ", ".join(times[:12]))
