# -*- coding: utf-8 -*-
import json
import os
import urllib.request
from datetime import datetime, timezone, timedelta

ENV = r"c:\Users\GC1\Desktop\Automação GHL\.env"
key = None
with open(ENV, encoding="utf-8") as f:
    for line in f:
        if line.startswith("GHL_MULTIODONTO_API_KEY="):
            key = line.split("=", 1)[1].strip()
            break
assert key

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
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"{method} {url} -> {e.code} {err}")


def hour(oh, om, ch, cm):
    return {"openHour": oh, "openMinute": om, "closeHour": ch, "closeMinute": cm}


def day(days, hours):
    return {"daysOfTheWeek": days if isinstance(days, list) else [days], "hours": hours}


hours_castro = [
    day(3, [hour(9, 0, 12, 0), hour(13, 0, 19, 0)]),
    day(4, [hour(9, 0, 12, 0), hour(13, 0, 19, 0)]),
    day(6, [hour(9, 0, 13, 30)]),
]
hours_giovanna = [
    day(1, [hour(9, 0, 12, 0), hour(13, 0, 19, 0)]),
    day(4, [hour(9, 0, 12, 0), hour(13, 0, 19, 0)]),
    day(6, [hour(9, 0, 13, 30)]),
]
hours_thais = [day(5, [hour(9, 0, 12, 0), hour(13, 0, 19, 0)])]
hours_rafael = [
    day(1, [hour(9, 0, 13, 0), hour(14, 0, 19, 0)]),
    day(3, [hour(9, 0, 13, 0), hour(14, 0, 19, 0)]),
]
hours_juliana = [
    day(1, [hour(11, 0, 13, 0), hour(14, 0, 18, 0)]),
    day(3, [hour(11, 0, 13, 0), hour(14, 0, 18, 0)]),
    day(2, [hour(9, 0, 13, 0), hour(14, 0, 17, 0)]),
    day(4, [hour(9, 0, 13, 0), hour(14, 0, 14, 50)]),
]
hours_personal = [
    day(d, [hour(8, 0, 19, 0)]) for d in (1, 2, 3, 4, 5, 6)
]

calendars = {
    "Castro": ("dpnGTRPb4wLTjWxPfO3M", hours_castro),
    "GiovannaCG": ("ACcmwEr9OeexBtiU4yl6", hours_giovanna),
    "Thais": ("bOur6KKgSm1cQvIxYnwQ", hours_thais),
    "RafaelCG": ("Sq4S1RHRaAoVfLbcb6Gj", hours_rafael),
    "Juliana": ("1X5AaBX8WCmn4FpAuMxJ", hours_juliana),
    "PersonalLucas": ("FGfn83WOGnzzrlqQHLhJ", hours_personal),
    "PersonalCaroline": ("JBdqRPhuBsi0oVmjZ0CF", hours_personal),
    "PersonalThais": ("NVFlLkuvyDpIVPnaGXnq", hours_personal),
    "PersonalLuis": ("BPYDKRaRVsDhA9lkOXxz", hours_personal),
    "PersonalJuliana": ("x24CJMJMuK2YJaZUuRRD", hours_personal),
}


def summarize(oh):
    names = {0: "Dom", 1: "Seg", 2: "Ter", 3: "Qua", 4: "Qui", 5: "Sex", 6: "Sab"}
    parts = []
    for block in oh or []:
        ds = ",".join(names.get(int(x), str(x)) for x in block.get("daysOfTheWeek", []))
        hs = []
        for h in block.get("hours", []):
            hs.append(
                f"{h['openHour']:02d}:{h['openMinute']:02d}-{h['closeHour']:02d}:{h['closeMinute']:02d}"
            )
        parts.append(f"{ds}:{';'.join(hs)}")
    return " | ".join(parts)


for label, (cid, hours) in calendars.items():
    cur = req("GET", f"https://services.leadconnectorhq.com/calendars/{cid}")
    cal = cur.get("calendar", cur)
    body = {"openHours": hours, "teamMembers": cal.get("teamMembers", [])}
    resp = req("PUT", f"https://services.leadconnectorhq.com/calendars/{cid}", body, version="2021-04-15")
    out = resp.get("calendar", resp)
    users = ",".join(m.get("userId", "") for m in out.get("teamMembers", []))
    print(f"OK {label} days={summarize(out.get('openHours'))} user={users}")

tz = timezone(timedelta(hours=-3))
ids_check = {
    "Scherres": "fUvShjVjDVERgGZUuNls",
    "Castro": "dpnGTRPb4wLTjWxPfO3M",
    "Giovanna": "ACcmwEr9OeexBtiU4yl6",
    "Thais": "bOur6KKgSm1cQvIxYnwQ",
    "Rafael": "Sq4S1RHRaAoVfLbcb6Gj",
    "Juliana": "1X5AaBX8WCmn4FpAuMxJ",
}
print("\n=== SLOTS ===")
for day_s in ["2026-08-17", "2026-08-19", "2026-08-20", "2026-08-21", "2026-08-22", "2026-08-29"]:
    start = datetime.fromisoformat(f"{day_s}T00:00:00").replace(tzinfo=tz)
    end = start + timedelta(days=1)
    s = int(start.timestamp() * 1000)
    e = int(end.timestamp() * 1000)
    bits = [day_s]
    for name, cid in ids_check.items():
        sl = req(
            "GET",
            f"https://services.leadconnectorhq.com/calendars/{cid}/free-slots?startDate={s}&endDate={e}",
        )
        n = len(sl.get(day_s, {}).get("slots") or [])
        bits.append(f"{name}={n}")
        if day_s == "2026-08-22" and name in ("Scherres", "Castro", "Giovanna") and n:
            bits.append("[" + ",".join(sl[day_s]["slots"][:8]) + "]")
    print(" ".join(bits))
