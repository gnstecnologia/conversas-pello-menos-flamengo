# -*- coding: utf-8 -*-
import json
import urllib.request

ENV = r"c:\Users\GC1\Desktop\Automação GHL\.env"
key = None
with open(ENV, encoding="utf-8") as f:
    for line in f:
        if line.startswith("GHL_MULTIODONTO_API_KEY="):
            key = line.split("=", 1)[1].strip()
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"


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


out = r"c:\Users\GC1\Desktop\Automação GHL\multiodonto-audit"
for name, cid in [("castro", "dpnGTRPb4wLTjWxPfO3M"), ("scherres", "fUvShjVjDVERgGZUuNls"), ("giovanna", "ACcmwEr9OeexBtiU4yl6")]:
    cal = req("GET", f"https://services.leadconnectorhq.com/calendars/{cid}")
    cal = cal.get("calendar", cal)
    with open(f"{out}\\cal-{name}-after.json", "w", encoding="utf-8") as f:
        json.dump(cal, f, ensure_ascii=False, indent=2)
    print(name, "openHours type", type(cal.get("openHours")).__name__, "len", len(cal.get("openHours") or []))

for uid, label in [("NYRiXy9cQ6TLG6Jwx4Pa", "lucas"), ("BkNWYQpSwyaPIKkGHDuQ", "caroline"), ("GDki1dJn6gcdMYzzGaaf", "agendas")]:
    try:
        u = req("GET", f"https://services.leadconnectorhq.com/users/{uid}")
        with open(f"{out}\\user-{label}.json", "w", encoding="utf-8") as f:
            json.dump(u, f, ensure_ascii=False, indent=2)
        user = u.get("user", u)
        print(label, "email", user.get("email"), "keys", [k for k in user.keys() if any(x in k.lower() for x in ("cal", "google", "avail", "role", "loc"))])
    except urllib.error.HTTPError as e:
        print(label, "user err", e.code, e.read()[:200])

# diagnostic: temporarily check if putting Castro onto Agendas Gerais unlocks Saturday
# We'll PUT then check 29/08 then PUT back to Lucas.
from datetime import datetime, timedelta, timezone

tz = timezone(timedelta(hours=-3))
day_s = "2026-08-29"
start = datetime.fromisoformat(f"{day_s}T00:00:00").replace(tzinfo=tz)
end = start + timedelta(days=1)
s = int(start.timestamp() * 1000)
e = int(end.timestamp() * 1000)

castro = req("GET", "https://services.leadconnectorhq.com/calendars/dpnGTRPb4wLTjWxPfO3M")
castro = castro.get("calendar", castro)
orig_tm = castro["teamMembers"]

agendas_tm = [
    {
        "priority": 0.5,
        "selected": True,
        "userId": "GDki1dJn6gcdMYzzGaaf",
        "isPrimary": True,
        "isZoomAdded": "false",
        "locationConfigurations": [
            {"kind": "custom", "location": "", "position": 0, "zoomOauthId": "", "meetingId": "custom_0"}
        ],
    }
]

print("\n--- test Castro assigned to Agendas Gerais ---")
req(
    "PUT",
    "https://services.leadconnectorhq.com/calendars/dpnGTRPb4wLTjWxPfO3M",
    {"openHours": castro["openHours"], "teamMembers": agendas_tm},
    version="2021-04-15",
)
sl = req("GET", f"https://services.leadconnectorhq.com/calendars/dpnGTRPb4wLTjWxPfO3M/free-slots?startDate={s}&endDate={e}")
print("Castro 29 with Agendas", len((sl.get(day_s) or {}).get("slots") or []), sl.get(day_s))

print("--- restore Castro to Lucas ---")
req(
    "PUT",
    "https://services.leadconnectorhq.com/calendars/dpnGTRPb4wLTjWxPfO3M",
    {"openHours": castro["openHours"], "teamMembers": orig_tm},
    version="2021-04-15",
)
sl2 = req("GET", f"https://services.leadconnectorhq.com/calendars/dpnGTRPb4wLTjWxPfO3M/free-slots?startDate={s}&endDate={e}")
print("Castro 29 with Lucas", len((sl2.get(day_s) or {}).get("slots") or []))
# confirm user restored
cal = req("GET", "https://services.leadconnectorhq.com/calendars/dpnGTRPb4wLTjWxPfO3M")
cal = cal.get("calendar", cal)
print("restored user", cal["teamMembers"][0]["userId"], "hours days", [x.get("daysOfTheWeek") for x in cal.get("openHours") or []])
