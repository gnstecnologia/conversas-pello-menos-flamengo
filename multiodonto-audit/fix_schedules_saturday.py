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
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        print("ERR", method, url, e.code, err[:800])
        return None


def tm(uid):
    return [{
        "priority": 0.5,
        "selected": True,
        "userId": uid,
        "isPrimary": True,
        "isZoomAdded": "false",
        "locationConfigurations": [
            {"kind": "custom", "location": "", "position": 0, "zoomOauthId": "", "meetingId": "custom_0"}
        ],
    }]


hours_scherres = [
    {"daysOfTheWeek": [2], "hours": [{"openHour": 9, "openMinute": 0, "closeHour": 13, "closeMinute": 0}, {"openHour": 14, "openMinute": 0, "closeHour": 19, "closeMinute": 0}]},
    {"daysOfTheWeek": [5], "hours": [{"openHour": 9, "openMinute": 0, "closeHour": 13, "closeMinute": 0}, {"openHour": 14, "openMinute": 0, "closeHour": 19, "closeMinute": 0}]},
    {"daysOfTheWeek": [6], "hours": [{"openHour": 9, "openMinute": 0, "closeHour": 13, "closeMinute": 30}]},
]
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

UID_AGENDAS = "GDki1dJn6gcdMYzzGaaf"
UID_CARLOS = "QNUDmXSAzlzngGr04uep"
UID_LUCAS = "NYRiXy9cQ6TLG6Jwx4Pa"
UID_CASTRO = "SFbV1M78uxKSfzCSnjML"
UID_GIOVANNA = "RvOJa0VXfQ7J91dq9tpG"
CAL_SCHERRES = "fUvShjVjDVERgGZUuNls"
CAL_CASTRO = "dpnGTRPb4wLTjWxPfO3M"
CAL_GIOVANNA = "ACcmwEr9OeexBtiU4yl6"

# restore Scherres hours without changing user
print("=== restore Scherres hours ===")
req("PUT", f"https://services.leadconnectorhq.com/calendars/{CAL_SCHERRES}", {
    "openHours": hours_scherres,
    "teamMembers": tm(UID_AGENDAS),
})

print("=== schedules ===")
for uid, label in [
    (UID_AGENDAS, "Agendas"),
    (UID_CARLOS, "Carlos"),
    (UID_LUCAS, "Lucas"),
    (UID_CASTRO, "AgendaCastro"),
    (UID_GIOVANNA, "AgendaGiovanna"),
]:
    data = req("GET", f"https://services.leadconnectorhq.com/calendars/schedules/search?locationId={LOC}&userId={uid}")
    print(f"\n{label}")
    print(json.dumps(data, ensure_ascii=False)[:1200] if data is not None else None)

sat_rules = [
    {"type": "wday", "day": d, "intervals": [{"from": "08:00", "to": "19:00"}]}
    for d in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]
]

def ensure_sat_schedule(uid, name, calendar_ids):
    data = req("GET", f"https://services.leadconnectorhq.com/calendars/schedules/search?locationId={LOC}&userId={uid}")
    schedules = []
    if isinstance(data, dict):
        schedules = data.get("schedules") or data.get("data") or []
        if not schedules and data.get("id"):
            schedules = [data]
    if schedules:
        sch = schedules[0]
        sid = sch.get("id")
        print("updating schedule", name, sid)
        resp = req("PUT", f"https://services.leadconnectorhq.com/calendars/schedules/{sid}", {
            "name": sch.get("name") or name,
            "timezone": sch.get("timezone") or "America/Sao_Paulo",
            "rules": sat_rules,
        })
        print("updated", json.dumps(resp, ensure_ascii=False)[:400] if resp else None)
        for cid in calendar_ids:
            assoc = req("PUT", f"https://services.leadconnectorhq.com/calendars/schedules/{sid}/associations/{cid}")
            print("assoc", cid, assoc)
        return sid
    print("creating schedule", name)
    resp = req("POST", "https://services.leadconnectorhq.com/calendars/schedules", {
        "name": name,
        "timezone": "America/Sao_Paulo",
        "locationId": LOC,
        "userId": uid,
        "calendarIds": calendar_ids,
        "rules": sat_rules,
    })
    print("created", json.dumps(resp, ensure_ascii=False)[:500] if resp else None)
    return (resp or {}).get("schedule", resp or {}).get("id")

print("\n=== ensure schedules ===")
ensure_sat_schedule(UID_CASTRO, "Agenda Castro CG - com sabado", [CAL_CASTRO])
ensure_sat_schedule(UID_GIOVANNA, "Agenda Giovanna CG - com sabado", [CAL_GIOVANNA])

# keep assignments + hours
req("PUT", f"https://services.leadconnectorhq.com/calendars/{CAL_CASTRO}", {"openHours": hours_castro, "teamMembers": tm(UID_CASTRO)})
req("PUT", f"https://services.leadconnectorhq.com/calendars/{CAL_GIOVANNA}", {"openHours": hours_giovanna, "teamMembers": tm(UID_GIOVANNA)})

tz = timezone(timedelta(hours=-3))
print("\n=== SLOTS ===")
for day_s in ["2026-08-22", "2026-08-29"]:
    start = datetime.fromisoformat(f"{day_s}T00:00:00").replace(tzinfo=tz)
    end = start + timedelta(days=1)
    s = int(start.timestamp() * 1000)
    e = int(end.timestamp() * 1000)
    parts = [day_s]
    for name, cid in [("Scherres", CAL_SCHERRES), ("Castro", CAL_CASTRO), ("Giovanna", CAL_GIOVANNA)]:
        sl = req("GET", f"https://services.leadconnectorhq.com/calendars/{cid}/free-slots?startDate={s}&endDate={e}", version="2021-07-28")
        slots = ((sl or {}).get(day_s) or {}).get("slots") or []
        parts.append(f"{name}={len(slots)}")
        if slots:
            parts.append("[" + ",".join(x[11:16] for x in slots) + "]")
    print(" ".join(parts))
