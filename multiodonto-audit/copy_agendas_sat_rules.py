# -*- coding: utf-8 -*-
import json
import urllib.request
from datetime import datetime, timedelta, timezone

ENV = r"c:\Users\GC1\Desktop\Automação GHL\.env"
key = None
with open(ENV, encoding="utf-8") as f:
    for line in f:
        if line.startswith("GHL_MULTIODONTO_API_KEY="):
            key = line.split("=", 1)[1].strip()
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"


def req(method, url, body=None, version="2021-04-15"):
    data = None if body is None else json.dumps(body).encode("utf-8")
    r = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {key}",
            "Version": version,
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": UA,
        },
    )
    with urllib.request.urlopen(r, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


# Exact copy of Agendas Gerais Work Hours
rules = [
    {"type": "wday", "day": "monday", "intervals": [{"from": "00:00", "to": "00:00"}]},
    {"type": "wday", "day": "tuesday", "intervals": [{"from": "00:00", "to": "00:00"}]},
    {"type": "wday", "day": "wednesday", "intervals": [{"from": "00:00", "to": "00:00"}]},
    {"type": "wday", "day": "thursday", "intervals": [{"from": "00:00", "to": "00:00"}]},
    {"type": "wday", "day": "friday", "intervals": [{"from": "00:00", "to": "00:00"}]},
    {"type": "wday", "day": "saturday", "intervals": [{"from": "09:00", "to": "13:30"}]},
]

for sid in ["po6k3xkQUjES6un0nUWl", "ROe8QU4AvdCD6tYbYgMS"]:
    resp = req("PUT", f"https://services.leadconnectorhq.com/calendars/schedules/{sid}", {
        "timezone": "America/Sao_Paulo",
        "rules": rules,
    })
    sch = resp.get("schedule", resp)
    sat = [r for r in sch.get("rules", []) if r.get("day") == "saturday"]
    print(sid, "sat", sat)

tz = timezone(timedelta(hours=-3))
print("\n=== SLOTS ===")
ids = {
    "Scherres": "fUvShjVjDVERgGZUuNls",
    "Castro": "dpnGTRPb4wLTjWxPfO3M",
    "Giovanna": "ACcmwEr9OeexBtiU4yl6",
}
for day_s in ["2026-08-22", "2026-08-29"]:
    start = datetime.fromisoformat(f"{day_s}T00:00:00").replace(tzinfo=tz)
    s = int(start.timestamp() * 1000)
    e = int((start + timedelta(days=1)).timestamp() * 1000)
    parts = [day_s]
    for name, cid in ids.items():
        sl = req("GET", f"https://services.leadconnectorhq.com/calendars/{cid}/free-slots?startDate={s}&endDate={e}", version="2021-07-28")
        slots = (sl.get(day_s) or {}).get("slots") or []
        parts.append(f"{name}={len(slots)}")
        if slots:
            parts.append("[" + ",".join(x[11:16] for x in slots) + "]")
    print(" ".join(parts))
