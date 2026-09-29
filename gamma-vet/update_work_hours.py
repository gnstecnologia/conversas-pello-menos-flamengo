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
SID = "qFMZOj1GjAfLRsORSMj7"
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
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        print("ERR", method, e.code, e.read().decode("utf-8", errors="replace")[:1000])
        return None


def wday(day, fr, to):
    return {"type": "wday", "day": day, "intervals": [{"from": fr, "to": to}]}


rules = [
    wday("monday", "08:00", "18:00"),
    wday("tuesday", "08:00", "18:00"),
    wday("wednesday", "08:00", "18:00"),
    wday("thursday", "08:00", "18:00"),
    wday("friday", "08:00", "18:00"),
    wday("saturday", "08:00", "13:00"),
]
out = req(
    "PUT",
    f"https://services.leadconnectorhq.com/calendars/schedules/{SID}",
    {"name": "Work Hours", "timezone": "America/Sao_Paulo", "rules": rules},
)
sch = (out or {}).get("schedule", out) or out
print("updated days", [r.get("day") for r in (sch.get("rules") or [])] if isinstance(sch, dict) else sch)

ids = json.loads(
    open(r"c:\Users\GC1\Desktop\Automação GHL\gamma-vet\calendar-ids-live.json", encoding="utf-8").read()
)
tz = timezone(timedelta(hours=-3))
print("\n=== SLOTS após Work Hours ===")
cals = {
    "Fernanda": ids["fernanda"],
    "Luciana": ids["luciana"],
    "RX": ids["rx"],
    "TC": ids["tomo"],
    "Cintilo": ids["cintilo"],
}
days = ["2026-08-17", "2026-08-19", "2026-08-20", "2026-08-21", "2026-08-22"]
print("data       " + " ".join(f"{k:>9}" for k in cals))
for day_s in days:
    start = datetime.fromisoformat(f"{day_s}T00:00:00").replace(tzinfo=tz)
    s = int(start.timestamp() * 1000)
    e = int((start + timedelta(days=1)).timestamp() * 1000)
    parts = [day_s]
    for cid in cals.values():
        sl = req(
            "GET",
            f"https://services.leadconnectorhq.com/calendars/{cid}/free-slots?startDate={s}&endDate={e}",
            version="2021-07-28",
        ) or {}
        n = len((sl.get(day_s) or {}).get("slots") or [])
        parts.append(f"{n:9d}")
    print(" ".join(parts))
