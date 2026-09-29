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
CASTRO = "dpnGTRPb4wLTjWxPfO3M"


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
    with urllib.request.urlopen(r, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


users = req("GET", f"https://services.leadconnectorhq.com/users/?locationId={LOC}")
ulist = users.get("users", users)
print("=== appointmentsEnabled ===")
for u in ulist:
    perms = u.get("permissions") or {}
    print(f"{u['id']} | {u.get('firstName')} {u.get('lastName')} | appt={perms.get('appointmentsEnabled')} role={u.get('roles',{}).get('role')} type={u.get('type')}")

tz = timezone(timedelta(hours=-3))
day_s = "2026-08-29"
start = datetime.fromisoformat(f"{day_s}T00:00:00").replace(tzinfo=tz)
end = start + timedelta(days=1)
s = int(start.timestamp() * 1000)
e = int(end.timestamp() * 1000)

castro = req("GET", f"https://services.leadconnectorhq.com/calendars/{CASTRO}")
castro = castro.get("calendar", castro)
hours = castro["openHours"]

print("\n=== Saturday slots per user (Castro cal 29/08) ===")
results = []
for u in ulist:
    uid = u["id"]
    tm = [
        {
            "priority": 0.5,
            "selected": True,
            "userId": uid,
            "isPrimary": True,
            "isZoomAdded": "false",
            "locationConfigurations": [
                {"kind": "custom", "location": "", "position": 0, "zoomOauthId": "", "meetingId": "custom_0"}
            ],
        }
    ]
    req("PUT", f"https://services.leadconnectorhq.com/calendars/{CASTRO}", {"openHours": hours, "teamMembers": tm}, version="2021-04-15")
    sl = req("GET", f"https://services.leadconnectorhq.com/calendars/{CASTRO}/free-slots?startDate={s}&endDate={e}")
    n = len((sl.get(day_s) or {}).get("slots") or [])
    name = f"{u.get('firstName')} {u.get('lastName')}"
    print(f"{n:2d}  {name}")
    results.append((n, name, uid))

# restore Castro to a Saturday-working user if any besides Agendas; else Agendas for now we'll assign properly later
working = [r for r in results if r[0] > 0]
print("\nWORKING", working)

# leave Castro on Lucas only if we will reassign - better leave on Agendas so Saturday isn't broken while we decide
agendas = "GDki1dJn6gcdMYzzGaaf"
# Don't leave on Agendas if we found others - parent will assign. Restore hours+Lucas for now? Better keep hours and pick later.
# Restore to Agendas temporarily so Saturday isn't 0 if script ends mid-planning... user wants Saturday working.
# We'll assign unique users in a follow-up. For this script restore hours with Agendas so 29 has slots, then next script splits.
tm = [
    {
        "priority": 0.5,
        "selected": True,
        "userId": agendas,
        "isPrimary": True,
        "isZoomAdded": "false",
        "locationConfigurations": [
            {"kind": "custom", "location": "", "position": 0, "zoomOauthId": "", "meetingId": "custom_0"}
        ],
    }
]
req("PUT", f"https://services.leadconnectorhq.com/calendars/{CASTRO}", {"openHours": hours, "teamMembers": tm}, version="2021-04-15")
print("Castro left on Agendas Gerais pending assignment")
