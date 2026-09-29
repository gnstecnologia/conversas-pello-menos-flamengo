# -*- coding: utf-8 -*-
import json
import urllib.request
import urllib.error

ENV = r"c:\Users\GC1\Desktop\Automação GHL\.env"
vals = {}
with open(ENV, encoding="utf-8") as f:
    for line in f:
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            vals[k.strip()] = v.strip()

KEY = vals["GHL_GAMMA_API_KEY"]
LOC = vals["GHL_GAMMA_LOCATION_ID"]
UID = "LxQOtMzWVhRqNLlWnLCI"
UA = "Mozilla/5.0"


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
        print("ERR", method, e.code, e.read().decode("utf-8", errors="replace")[:1200])
        return None


hours = [{
    "daysOfTheWeek": [1],
    "hours": [{"openHour": 8, "openMinute": 30, "closeHour": 18, "closeMinute": 0}],
}]
tm = [{
    "priority": 0.5,
    "selected": True,
    "userId": UID,
    "isPrimary": True,
    "isZoomAdded": "false",
    "locationConfigurations": [
        {"kind": "custom", "location": "", "position": 0, "zoomOauthId": "", "meetingId": "custom_0"}
    ],
}]

payload = {
    "locationId": LOC,
    "name": "TEST occupancy Fernanda — apagar",
    "description": "calendario de teste, apagar",
    "calendarType": "service_booking",
    "eventType": "RoundRobin_OptimizeForEqualDistribution",
    "slotDuration": 30,
    "slotDurationUnit": "mins",
    "slotInterval": 30,
    "slotIntervalUnit": "mins",
    "appointmentPerSlot": 1,
    "openHours": hours,
    "teamMembers": tm,
    "isActive": False,
    "autoConfirm": True,
}
created = req("POST", "https://services.leadconnectorhq.com/calendars/", payload)
if not created:
    raise SystemExit("create failed")
cal = created.get("calendar", created)
cid = cal.get("id")
print("created", cid, "type", cal.get("calendarType"), "members", [m.get("userId") for m in (cal.get("teamMembers") or [])])

if cid:
    got = req("GET", f"https://services.leadconnectorhq.com/calendars/{cid}")
    g = (got or {}).get("calendar", got)
    print("GET type", g.get("calendarType"), "members", [m.get("userId") for m in (g.get("teamMembers") or [])])
    deleted = req("DELETE", f"https://services.leadconnectorhq.com/calendars/{cid}")
    print("deleted", deleted)
