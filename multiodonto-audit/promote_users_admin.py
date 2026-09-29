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


def req(method, url, body=None, version="2021-07-28"):
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
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print("ERR", method, url, e.code, e.read().decode("utf-8", errors="replace")[:700])
        return None


uids = {
    "AgendaCastro": "SFbV1M78uxKSfzCSnjML",
    "AgendaGiovanna": "RvOJa0VXfQ7J91dq9tpG",
}
for label, uid in uids.items():
    body = {
        "type": "account",
        "role": "admin",
        "locationIds": [LOC],
    }
    resp = req("PUT", f"https://services.leadconnectorhq.com/users/{uid}", body)
    user = (resp or {}).get("user", resp or {})
    print(label, "role", user.get("roles"), "id", user.get("id"))

hours_castro = [
    {"daysOfTheWeek": [3], "hours": [{"openHour": 9, "openMinute": 0, "closeHour": 12, "closeMinute": 0}, {"openHour": 13, "openMinute": 0, "closeHour": 19, "closeMinute": 0}]},
    {"daysOfTheWeek": [4], "hours": [{"openHour": 9, "openMinute": 0, "closeHour": 12, "closeMinute": 0}, {"openHour": 13, "openMinute": 0, "closeHour": 19, "closeMinute": 0}]},
    {"daysOfTheWeek": [6], "hours": [{"openHour": 9, "openMinute": 0, "closeHour": 13, "closeMinute": 30}]},
]
hours_giovanna = [
    {"daysOfTheWeek": [1], "hours": [{"openHour": 9, "openMinute": 0, "closeHour": 12, "closeMinute": 0}, {"openHour": 13, "openMinute": 0, "closeHour": 19, "closeMinute": 0}]},
    {"daysOfTheWeek": [4], "hours": [{"openHour": 9, "openMinute": 0, "closeHour": 12, "closeMinute": 0}, {"openHour": 13, "openMinute": 0, "closeHour": 19, "closeMinute": 0}]},
    {"daysOfTheWeek": [6], "hours": [{"openHour": 9, "openMinute": 0, "closeHour": 13, "closeMinute": 30}]},
]

def tm(uid):
    return [{
        "priority": 0.5, "selected": True, "userId": uid, "isPrimary": True, "isZoomAdded": "false",
        "locationConfigurations": [{"kind": "custom", "location": "", "position": 0, "zoomOauthId": "", "meetingId": "custom_0"}],
    }]

req("PUT", "https://services.leadconnectorhq.com/calendars/dpnGTRPb4wLTjWxPfO3M", {"openHours": hours_castro, "teamMembers": tm("SFbV1M78uxKSfzCSnjML")}, version="2021-04-15")
req("PUT", "https://services.leadconnectorhq.com/calendars/ACcmwEr9OeexBtiU4yl6", {"openHours": hours_giovanna, "teamMembers": tm("RvOJa0VXfQ7J91dq9tpG")}, version="2021-04-15")

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
        sl = req("GET", f"https://services.leadconnectorhq.com/calendars/{cid}/free-slots?startDate={s}&endDate={e}")
        slots = ((sl or {}).get(day_s) or {}).get("slots") or []
        parts.append(f"{name}={len(slots)}")
        if slots:
            parts.append("[" + ",".join(x[11:16] for x in slots) + "]")
    print(" ".join(parts))
