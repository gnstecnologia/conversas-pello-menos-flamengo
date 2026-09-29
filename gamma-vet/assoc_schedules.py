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
SID = "qFMZOj1GjAfLRsORSMj7"
UA = "Mozilla/5.0"
ids = json.loads(open(r"c:\Users\GC1\Desktop\Automação GHL\gamma-vet\calendar-ids-live.json", encoding="utf-8").read())


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
        print("ERR", e.code, e.read().decode("utf-8", errors="replace")[:500])
        return None


for key in ("fernanda", "rx", "tomo"):
    out = req("PUT", f"https://services.leadconnectorhq.com/calendars/schedules/{SID}/associations/{ids[key]}")
    print("assoc", key, ids[key], out.get("success") if isinstance(out, dict) else out)

tz = timezone(timedelta(hours=-3))
print("\nslots")
days = ["2026-08-20", "2026-08-22"]
for day_s in days:
    start = datetime.fromisoformat(f"{day_s}T00:00:00").replace(tzinfo=tz)
    s = int(start.timestamp() * 1000)
    e = int((start + timedelta(days=1)).timestamp() * 1000)
    parts = [day_s]
    for key in ("fernanda", "luciana", "rx", "tomo", "cintilo"):
        sl = req(
            "GET",
            f"https://services.leadconnectorhq.com/calendars/{ids[key]}/free-slots?startDate={s}&endDate={e}",
            version="2021-07-28",
        ) or {}
        n = len((sl.get(day_s) or {}).get("slots") or [])
        parts.append(f"{key}={n}")
    print(" ".join(parts))
