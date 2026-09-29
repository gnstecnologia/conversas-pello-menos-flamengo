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
UA = "Mozilla/5.0"

CALS = {
    "fernanda": "67dUBkMOw78GdahUsc1t",
    "luciana": "djzQjTsrDhXWaj3LzjU6",
    "rx": "sZ984nPHX1C8X6ntMw1d",
    "tomo": "xxgHhAzTmq6GgntlmYV5",
    "cintilo": "HeFRPrO55KkQjhfJIaNc",
}


def req(method, url, version="2021-04-15"):
    r = urllib.request.Request(
        url,
        method=method,
        headers={
            "Authorization": f"Bearer {KEY}",
            "Version": version,
            "Accept": "application/json",
            "User-Agent": UA,
        },
    )
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print("ERR", e.code, e.read().decode("utf-8", errors="replace")[:400])
        return {}


tz = timezone(timedelta(hours=-3))
start = datetime(2026, 8, 1, tzinfo=tz)
end = datetime(2026, 10, 1, tzinfo=tz)
s = int(start.timestamp() * 1000)
e = int(end.timestamp() * 1000)

for name, cid in CALS.items():
    data = req(
        "GET",
        f"https://services.leadconnectorhq.com/calendars/events?locationId={LOC}&calendarId={cid}&startTime={s}&endTime={e}",
        version="2021-07-28",
    )
    evs = data.get("events") or []
    print(name, "events", len(evs))
    for ev in evs[:8]:
        print(" ", ev.get("startTime"), ev.get("title"), ev.get("appointmentStatus"), ev.get("id"))
