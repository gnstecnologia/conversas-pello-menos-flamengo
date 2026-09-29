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
CAL_CASTRO = "dpnGTRPb4wLTjWxPfO3M"
UID_CARLOS = "QNUDmXSAzlzngGr04uep"
UID_CASTRO = "SFbV1M78uxKSfzCSnjML"
SID_CASTRO = "po6k3xkQUjES6un0nUWl"


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
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        print("ERR", e.code, e.read().decode("utf-8", errors="replace")[:500])
        return None


def tm(uid):
    return [{
        "priority": 0.5, "selected": True, "userId": uid, "isPrimary": True, "isZoomAdded": "false",
        "locationConfigurations": [{"kind": "custom", "location": "", "position": 0, "zoomOauthId": "", "meetingId": "custom_0"}],
    }]

hours_castro = [
    {"daysOfTheWeek": [3], "hours": [{"openHour": 9, "openMinute": 0, "closeHour": 12, "closeMinute": 0}, {"openHour": 13, "openMinute": 0, "closeHour": 19, "closeMinute": 0}]},
    {"daysOfTheWeek": [4], "hours": [{"openHour": 9, "openMinute": 0, "closeHour": 12, "closeMinute": 0}, {"openHour": 13, "openMinute": 0, "closeHour": 19, "closeMinute": 0}]},
    {"daysOfTheWeek": [6], "hours": [{"openHour": 9, "openMinute": 0, "closeHour": 13, "closeMinute": 30}]},
]

tz = timezone(timedelta(hours=-3))
day_s = "2026-08-29"
s = int(datetime.fromisoformat(f"{day_s}T00:00:00").replace(tzinfo=tz).timestamp() * 1000)
e = int((datetime.fromisoformat(f"{day_s}T00:00:00").replace(tzinfo=tz) + timedelta(days=1)).timestamp() * 1000)

sch = req("GET", f"https://services.leadconnectorhq.com/calendars/schedules/{SID_CASTRO}")
print("schedule Castro user", json.dumps(sch, ensure_ascii=False)[:800])

print("remove association")
req("DELETE", f"https://services.leadconnectorhq.com/calendars/schedules/{SID_CASTRO}/associations/{CAL_CASTRO}")
sch = req("GET", f"https://services.leadconnectorhq.com/calendars/schedules/{SID_CASTRO}")
print("after delete assoc", json.dumps((sch or {}).get("schedule", sch), ensure_ascii=False)[:500])

req("PUT", f"https://services.leadconnectorhq.com/calendars/{CAL_CASTRO}", {"openHours": hours_castro, "teamMembers": tm(UID_CASTRO)})
sl = req("GET", f"https://services.leadconnectorhq.com/calendars/{CAL_CASTRO}/free-slots?startDate={s}&endDate={e}", version="2021-07-28")
print("new user no assoc", len((sl.get(day_s) or {}).get("slots") or []))

print("assign Carlos")
req("PUT", f"https://services.leadconnectorhq.com/calendars/{CAL_CASTRO}", {"openHours": hours_castro, "teamMembers": tm(UID_CARLOS)})
sl = req("GET", f"https://services.leadconnectorhq.com/calendars/{CAL_CASTRO}/free-slots?startDate={s}&endDate={e}", version="2021-07-28")
print("Carlos", len((sl.get(day_s) or {}).get("slots") or []), (sl.get(day_s) or {}).get("slots"))

print("assign new user again")
req("PUT", f"https://services.leadconnectorhq.com/calendars/{CAL_CASTRO}", {"openHours": hours_castro, "teamMembers": tm(UID_CASTRO)})
sl = req("GET", f"https://services.leadconnectorhq.com/calendars/{CAL_CASTRO}/free-slots?startDate={s}&endDate={e}", version="2021-07-28")
print("new user again", len((sl.get(day_s) or {}).get("slots") or []))

# permissions compare
for uid, label in [(UID_CARLOS, "Carlos"), (UID_CASTRO, "AgendaCastro")]:
    u = req("GET", f"https://services.leadconnectorhq.com/users/{uid}", version="2021-07-28")
    user = u.get("user", u)
    print(label, "role", user.get("roles"), "appt", (user.get("permissions") or {}).get("appointmentsEnabled"), "type", user.get("type"))
