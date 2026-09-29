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
UID_THAIS = "KblUZVSnolCs2DEEkDFM"
UID_JULIANA = "BnbTWPQRn5HxtLbbcI0w"
UID_LUIS = "GbS8Nm1TONkkpsQdmLL5"


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

rules_sat = [
    {"type": "wday", "day": "monday", "intervals": [{"from": "00:00", "to": "00:00"}]},
    {"type": "wday", "day": "tuesday", "intervals": [{"from": "00:00", "to": "00:00"}]},
    {"type": "wday", "day": "wednesday", "intervals": [{"from": "00:00", "to": "00:00"}]},
    {"type": "wday", "day": "thursday", "intervals": [{"from": "00:00", "to": "00:00"}]},
    {"type": "wday", "day": "friday", "intervals": [{"from": "00:00", "to": "00:00"}]},
    {"type": "wday", "day": "saturday", "intervals": [{"from": "09:00", "to": "13:30"}]},
]

data = req("GET", f"https://services.leadconnectorhq.com/calendars/schedules/search?locationId={LOC}&userId={UID_CAROLINE}")
print("Caroline schedules", json.dumps(data, ensure_ascii=False)[:700])
sid = data["schedules"][0]["id"]
resp = req("PUT", f"https://services.leadconnectorhq.com/calendars/schedules/{sid}", {"timezone": "America/Sao_Paulo", "rules": rules_sat})
print("updated sat", [r for r in resp["schedule"]["rules"] if r["day"] == "saturday"])

req("PUT", f"https://services.leadconnectorhq.com/calendars/{CAL_CASTRO}", {"openHours": hours_castro, "teamMembers": tm(UID_CAROLINE)})

tz = timezone(timedelta(hours=-3))
day_s = "2026-08-29"
s = int(datetime.fromisoformat(f"{day_s}T00:00:00").replace(tzinfo=tz).timestamp() * 1000)
e = int((datetime.fromisoformat(f"{day_s}T00:00:00").replace(tzinfo=tz) + timedelta(days=1)).timestamp() * 1000)
sl = req("GET", f"https://services.leadconnectorhq.com/calendars/{CAL_CASTRO}/free-slots?startDate={s}&endDate={e}", version="2021-07-28")
print("Castro+Caroline after schedule sat", len((sl.get(day_s) or {}).get("slots") or []), (sl.get(day_s) or {}).get("slots"))
