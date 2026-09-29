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


def req(method, url, version="2021-07-28"):
    r = urllib.request.Request(
        url,
        method=method,
        headers={
            "Authorization": f"Bearer {key}",
            "Version": version,
            "Accept": "application/json",
            "User-Agent": UA,
        },
    )
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        print("ERR", method, url, e.code, err[:500])
        return None


def summarize(oh):
    names = {0: "Dom", 1: "Seg", 2: "Ter", 3: "Qua", 4: "Qui", 5: "Sex", 6: "Sab"}
    parts = []
    for block in oh or []:
        if not isinstance(block, dict):
            parts.append(str(block))
            continue
        ds = ",".join(names.get(int(x), str(x)) for x in block.get("daysOfTheWeek", []))
        hs = []
        for h in block.get("hours", []):
            hs.append(
                f"{h.get('openHour',0):02d}:{h.get('openMinute',0):02d}-{h.get('closeHour',0):02d}:{h.get('closeMinute',0):02d}"
            )
        parts.append(f"{ds}:{';'.join(hs)}")
    return " | ".join(parts) or "(vazio)"


ids = {
    "Castro": "dpnGTRPb4wLTjWxPfO3M",
    "Giovanna": "ACcmwEr9OeexBtiU4yl6",
    "Scherres": "fUvShjVjDVERgGZUuNls",
    "PersonalLucas": "FGfn83WOGnzzrlqQHLhJ",
    "PersonalCaroline": "JBdqRPhuBsi0oVmjZ0CF",
}
for name, cid in ids.items():
    cur = req("GET", f"https://services.leadconnectorhq.com/calendars/{cid}")
    cal = cur.get("calendar", cur) if cur else {}
    print(f"\n=== {name} ===")
    print("active", cal.get("isActive"), "type", cal.get("calendarType"), "event", cal.get("eventType"))
    print("hours", summarize(cal.get("openHours")))
    print("availabilities", json.dumps(cal.get("availabilities"), ensure_ascii=False)[:500])
    extra = {k: cal.get(k) for k in cal.keys() if any(x in k.lower() for x in ("time", "book", "google", "connect", "notice"))}
    print("extra", json.dumps(extra, ensure_ascii=False)[:900])

tz = timezone(timedelta(hours=-3))
start = datetime(2026, 8, 22, 0, 0, tzinfo=tz)
end = datetime(2026, 8, 30, 0, 0, tzinfo=tz)
s = int(start.timestamp() * 1000)
e = int(end.timestamp() * 1000)

print("\n=== EVENTS 22-29 ===")
for cal_name, cid in [("Castro", ids["Castro"]), ("Giovanna", ids["Giovanna"]), ("Scherres", ids["Scherres"])]:
    u = f"https://services.leadconnectorhq.com/calendars/events?locationId={LOC}&calendarId={cid}&startTime={s}&endTime={e}"
    data = req("GET", u)
    if not data:
        continue
    evs = data.get("events") or data.get("appointments") or data
    if isinstance(evs, dict):
        print(cal_name, "dict keys", list(evs.keys())[:15])
        print(json.dumps(evs)[:400])
    elif isinstance(evs, list):
        print(cal_name, "count", len(evs))
        for ev in evs:
            print(" ", ev.get("startTime"), ev.get("title"), ev.get("assignedUserId"), ev.get("appointmentStatus"), ev.get("id"))

print("\n=== USER EVENTS ===")
for uid, label in [("NYRiXy9cQ6TLG6Jwx4Pa", "Lucas"), ("BkNWYQpSwyaPIKkGHDuQ", "Caroline"), ("GDki1dJn6gcdMYzzGaaf", "Agendas")]:
    u = f"https://services.leadconnectorhq.com/calendars/events?locationId={LOC}&userId={uid}&startTime={s}&endTime={e}"
    data = req("GET", u)
    if not data:
        continue
    evs = data.get("events") or data.get("appointments") or []
    print(label, "count", len(evs) if isinstance(evs, list) else type(evs).__name__)
    if isinstance(evs, list):
        for ev in evs:
            st = str(ev.get("startTime", ""))
            if "2026-08-22" in st or "2026-08-29" in st:
                print(" ", st, ev.get("title"), ev.get("calendarId"), ev.get("appointmentStatus"))
