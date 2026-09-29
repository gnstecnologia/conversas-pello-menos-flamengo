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
LOC = "3R4hY0j3TJyj2SkmSQL3"


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


# Copy Agendas Gerais Work Hours pattern: 00:00-00:00 = sem restrição no user
agendas_rules = [
    {"type": "wday", "day": d, "intervals": [{"from": "00:00", "to": "00:00"}]}
    for d in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]
]

updates = {
    "SFbV1M78uxKSfzCSnjML": "po6k3xkQUjES6un0nUWl",
    "RvOJa0VXfQ7J91dq9tpG": "ROe8QU4AvdCD6tYbYgMS",
}
for uid, sid in updates.items():
    resp = req("PUT", f"https://services.leadconnectorhq.com/calendars/schedules/{sid}", {
        "timezone": "America/Sao_Paulo",
        "rules": agendas_rules,
    })
    sch = resp.get("schedule", resp)
    days = [(r.get("day"), r.get("intervals")) for r in sch.get("rules", [])]
    print(uid, days)

# also fix Thais/Juliana/Rafael users so weekdays aren't clipped at 17:00 if their service goes to 19
# skip for now

tz = timezone(timedelta(hours=-3))
print("\n=== SLOTS ===")
ids = {
    "Scherres": "fUvShjVjDVERgGZUuNls",
    "Castro": "dpnGTRPb4wLTjWxPfO3M",
    "Giovanna": "ACcmwEr9OeexBtiU4yl6",
}
for day_s in ["2026-08-17", "2026-08-19", "2026-08-21", "2026-08-22", "2026-08-29"]:
    start = datetime.fromisoformat(f"{day_s}T00:00:00").replace(tzinfo=tz)
    end = start + timedelta(days=1)
    s = int(start.timestamp() * 1000)
    e = int(end.timestamp() * 1000)
    parts = [day_s]
    for name, cid in ids.items():
        sl = req("GET", f"https://services.leadconnectorhq.com/calendars/{cid}/free-slots?startDate={s}&endDate={e}", version="2021-07-28")
        slots = (sl.get(day_s) or {}).get("slots") or []
        parts.append(f"{name}={len(slots)}")
        if day_s in ("2026-08-22", "2026-08-29") and slots:
            parts.append("[" + ",".join(x[11:16] for x in slots) + "]")
    print(" ".join(parts))
