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
UID = "LxQOtMzWVhRqNLlWnLCI"
CID = "67dUBkMOw78GdahUsc1t"
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
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print("ERR", e.code, e.read().decode("utf-8", errors="replace")[:1200])
        return None


cal = req("GET", f"https://services.leadconnectorhq.com/calendars/{CID}")
cal = (cal or {}).get("calendar", cal)
oh = cal.get("openHours")
print("type", cal.get("calendarType"), "eventType", cal.get("eventType"), "days", [x.get("daysOfTheWeek") for x in oh or []])

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

payloads = [
    {
        "openHours": oh,
        "calendarType": "service_booking",
        "teamMembers": tm,
    },
    {
        "openHours": oh,
        "calendarType": "service_booking",
        "eventType": "RoundRobin_OptimizeForEqualDistribution",
        "teamMembers": tm,
    },
]

for i, p in enumerate(payloads, 1):
    print("\nTRY", i, {k: p[k] for k in p if k != "openHours" and k != "teamMembers"})
    out = req("PUT", f"https://services.leadconnectorhq.com/calendars/{CID}", p)
    if not out:
        continue
    c = out.get("calendar", out)
    print(
        "  type", c.get("calendarType"),
        "eventType", c.get("eventType"),
        "members", [(m.get("userId"), m.get("selected")) for m in (c.get("teamMembers") or [])],
        "days", [x.get("daysOfTheWeek") for x in (c.get("openHours") or [])],
    )
    # if it worked, stop
    if c.get("teamMembers"):
        break
