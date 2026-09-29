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
UID_CAROLINE = "BkNWYQpSwyaPIKkGHDuQ"
SID_CAROLINE = "pwwEyy7JcOfFUg0bFp1j"
UID_CARLOS = "QNUDmXSAzlzngGr04uep"


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

rules = [
    {"type": "wday", "day": d, "intervals": [{"from": "00:00", "to": "00:00"}]}
    for d in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]
]
req("PUT", f"https://services.leadconnectorhq.com/calendars/schedules/{SID_CAROLINE}", {"timezone": "America/Sao_Paulo", "rules": rules})
req("PUT", f"https://services.leadconnectorhq.com/calendars/{CAL_CASTRO}", {"openHours": hours_castro, "teamMembers": tm(UID_CAROLINE)})

tz = timezone(timedelta(hours=-3))
day_s = "2026-08-29"
s = int(datetime.fromisoformat(f"{day_s}T00:00:00").replace(tzinfo=tz).timestamp() * 1000)
e = int((datetime.fromisoformat(f"{day_s}T00:00:00").replace(tzinfo=tz) + timedelta(days=1)).timestamp() * 1000)
sl = req("GET", f"https://services.leadconnectorhq.com/calendars/{CAL_CASTRO}/free-slots?startDate={s}&endDate={e}", version="2021-07-28")
print("Caroline 00:00 sat", len((sl.get(day_s) or {}).get("slots") or []))

# final assignment that actually works:
# Scherres = Agendas, Castro = Carlos, Giovanna = Agendas? still coupled
# Giovanna = Caroline if this works; else Carlos for Castro only and Giovanna stay Agendas (coupled with Scherres)

# Keep Castro on Carlos for production
req("PUT", f"https://services.leadconnectorhq.com/calendars/{CAL_CASTRO}", {"openHours": hours_castro, "teamMembers": tm(UID_CARLOS)})
sl = req("GET", f"https://services.leadconnectorhq.com/calendars/{CAL_CASTRO}/free-slots?startDate={s}&endDate={e}", version="2021-07-28")
print("Castro on Carlos", len((sl.get(day_s) or {}).get("slots") or []))
