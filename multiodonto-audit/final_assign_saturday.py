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

UID_AGENDAS = "GDki1dJn6gcdMYzzGaaf"
UID_CARLOS = "QNUDmXSAzlzngGr04uep"
UID_THAIS = "KblUZVSnolCs2DEEkDFM"
UID_JULIANA = "BnbTWPQRn5HxtLbbcI0w"
UID_LUIS = "GbS8Nm1TONkkpsQdmLL5"

CAL = {
    "Scherres": "fUvShjVjDVERgGZUuNls",
    "Castro": "dpnGTRPb4wLTjWxPfO3M",
    "Giovanna": "ACcmwEr9OeexBtiU4yl6",
    "Thais": "bOur6KKgSm1cQvIxYnwQ",
    "Rafael": "Sq4S1RHRaAoVfLbcb6Gj",
    "Juliana": "1X5AaBX8WCmn4FpAuMxJ",
}


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

hours = {
    "Scherres": [
        {"daysOfTheWeek": [2], "hours": [{"openHour": 9, "openMinute": 0, "closeHour": 13, "closeMinute": 0}, {"openHour": 14, "openMinute": 0, "closeHour": 19, "closeMinute": 0}]},
        {"daysOfTheWeek": [5], "hours": [{"openHour": 9, "openMinute": 0, "closeHour": 13, "closeMinute": 0}, {"openHour": 14, "openMinute": 0, "closeHour": 19, "closeMinute": 0}]},
        {"daysOfTheWeek": [6], "hours": [{"openHour": 9, "openMinute": 0, "closeHour": 13, "closeMinute": 30}]},
    ],
    "Castro": [
        {"daysOfTheWeek": [3], "hours": [{"openHour": 9, "openMinute": 0, "closeHour": 12, "closeMinute": 0}, {"openHour": 13, "openMinute": 0, "closeHour": 19, "closeMinute": 0}]},
        {"daysOfTheWeek": [4], "hours": [{"openHour": 9, "openMinute": 0, "closeHour": 12, "closeMinute": 0}, {"openHour": 13, "openMinute": 0, "closeHour": 19, "closeMinute": 0}]},
        {"daysOfTheWeek": [6], "hours": [{"openHour": 9, "openMinute": 0, "closeHour": 13, "closeMinute": 30}]},
    ],
    "Giovanna": [
        {"daysOfTheWeek": [1], "hours": [{"openHour": 9, "openMinute": 0, "closeHour": 12, "closeMinute": 0}, {"openHour": 13, "openMinute": 0, "closeHour": 19, "closeMinute": 0}]},
        {"daysOfTheWeek": [4], "hours": [{"openHour": 9, "openMinute": 0, "closeHour": 12, "closeMinute": 0}, {"openHour": 13, "openMinute": 0, "closeHour": 19, "closeMinute": 0}]},
        {"daysOfTheWeek": [6], "hours": [{"openHour": 9, "openMinute": 0, "closeHour": 13, "closeMinute": 30}]},
    ],
    "Thais": [
        {"daysOfTheWeek": [5], "hours": [{"openHour": 9, "openMinute": 0, "closeHour": 12, "closeMinute": 0}, {"openHour": 13, "openMinute": 0, "closeHour": 19, "closeMinute": 0}]},
    ],
    "Rafael": [
        {"daysOfTheWeek": [1], "hours": [{"openHour": 9, "openMinute": 0, "closeHour": 13, "closeMinute": 0}, {"openHour": 14, "openMinute": 0, "closeHour": 19, "closeMinute": 0}]},
        {"daysOfTheWeek": [3], "hours": [{"openHour": 9, "openMinute": 0, "closeHour": 13, "closeMinute": 0}, {"openHour": 14, "openMinute": 0, "closeHour": 19, "closeMinute": 0}]},
    ],
    "Juliana": [
        {"daysOfTheWeek": [1], "hours": [{"openHour": 11, "openMinute": 0, "closeHour": 13, "closeMinute": 0}, {"openHour": 14, "openMinute": 0, "closeHour": 18, "closeMinute": 0}]},
        {"daysOfTheWeek": [3], "hours": [{"openHour": 11, "openMinute": 0, "closeHour": 13, "closeMinute": 0}, {"openHour": 14, "openMinute": 0, "closeHour": 18, "closeMinute": 0}]},
        {"daysOfTheWeek": [2], "hours": [{"openHour": 9, "openMinute": 0, "closeHour": 13, "closeMinute": 0}, {"openHour": 14, "openMinute": 0, "closeHour": 17, "closeMinute": 0}]},
        {"daysOfTheWeek": [4], "hours": [{"openHour": 9, "openMinute": 0, "closeHour": 13, "closeMinute": 0}, {"openHour": 14, "openMinute": 0, "closeHour": 14, "closeMinute": 50}]},
    ],
}

users = {
    "Scherres": UID_AGENDAS,
    "Castro": UID_CARLOS,
    "Giovanna": UID_CARLOS,
    "Thais": UID_THAIS,
    "Rafael": UID_LUIS,
    "Juliana": UID_JULIANA,
}

# Carlos Saturday occupancy
tz = timezone(timedelta(hours=-3))
start = datetime(2026, 8, 22, 0, 0, tzinfo=tz)
end = datetime(2026, 8, 30, 0, 0, tzinfo=tz)
s0 = int(start.timestamp() * 1000)
e0 = int(end.timestamp() * 1000)
ev = req("GET", f"https://services.leadconnectorhq.com/calendars/events?locationId={LOC}&userId={UID_CARLOS}&startTime={s0}&endTime={e0}", version="2021-07-28")
evs = ev.get("events") or []
print("Carlos events 22-29:", len(evs))
for e in evs:
    st = str(e.get("startTime", ""))
    if "2026-08-22" in st or "2026-08-29" in st:
        print(" ", st, e.get("title"), e.get("calendarId"))

for name, cid in CAL.items():
    resp = req("PUT", f"https://services.leadconnectorhq.com/calendars/{cid}", {
        "openHours": hours[name],
        "teamMembers": tm(users[name]),
    })
    cal = resp.get("calendar", resp)
    print("OK", name, "user", cal["teamMembers"][0]["userId"], "days", [x.get("daysOfTheWeek") for x in cal.get("openHours") or []])

print("\n=== SLOTS ===")
for day_s in ["2026-08-17", "2026-08-19", "2026-08-21", "2026-08-22", "2026-08-29"]:
    start = datetime.fromisoformat(f"{day_s}T00:00:00").replace(tzinfo=tz)
    s = int(start.timestamp() * 1000)
    e = int((start + timedelta(days=1)).timestamp() * 1000)
    parts = [day_s]
    for name, cid in CAL.items():
        sl = req("GET", f"https://services.leadconnectorhq.com/calendars/{cid}/free-slots?startDate={s}&endDate={e}", version="2021-07-28")
        slots = (sl.get(day_s) or {}).get("slots") or []
        parts.append(f"{name}={len(slots)}")
        if day_s in ("2026-08-22", "2026-08-29") and name in ("Scherres", "Castro", "Giovanna") and slots:
            parts.append("[" + ",".join(x[11:16] for x in slots) + "]")
    print(" ".join(parts))
