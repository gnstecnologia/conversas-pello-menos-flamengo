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
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"

CALS = {
    "US Fernanda": "67dUBkMOw78GdahUsc1t",
    "US Luciana": "djzQjTsrDhXWaj3LzjU6",
    "Raio-X": "sZ984nPHX1C8X6ntMw1d",
    "Tomografia": "xxgHhAzTmq6GgntlmYV5",
    "Cintilografia": "HeFRPrO55KkQjhfJIaNc",
    "Radioiodo": "DFrcSX7SDJ5uJbz3qZ3C",
}


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
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        return e.code, err


def summarize(oh):
    names = {0: "Dom", 1: "Seg", 2: "Ter", 3: "Qua", 4: "Qui", 5: "Sex", 6: "Sab"}
    if not oh:
        return "(vazio)"
    if isinstance(oh, dict):
        return f"dict keys={list(oh.keys())[:8]}"
    parts = []
    for block in oh:
        ds = ",".join(names.get(int(x), str(x)) for x in block.get("daysOfTheWeek", []))
        hs = []
        for h in block.get("hours", []):
            hs.append(
                f"{h['openHour']:02d}:{h['openMinute']:02d}-{h['closeHour']:02d}:{h['closeMinute']:02d}"
            )
        parts.append(f"{ds}:{';'.join(hs)}")
    return " | ".join(parts)


code, users = req("GET", f"https://services.leadconnectorhq.com/users/?locationId={LOC}", version="2021-07-28")
print("USERS", code)
if isinstance(users, dict):
    for u in users.get("users") or []:
        print(
            " -",
            u.get("id"),
            u.get("name") or (str(u.get("firstName", "")) + " " + str(u.get("lastName", ""))),
            "email=",
            u.get("email"),
            "deleted=",
            u.get("deleted"),
        )
        wh = u.get("workHours") or u.get("calendarHours") or u.get("availability")
        if wh:
            print("   workHours keys", list(wh)[:20] if isinstance(wh, dict) else type(wh))
else:
    print(str(users)[:500])

print("\n=== CALENDARS ===")
for name, cid in CALS.items():
    code, body = req("GET", f"https://services.leadconnectorhq.com/calendars/{cid}")
    cal = body.get("calendar", body) if isinstance(body, dict) else {}
    tms = cal.get("teamMembers") or []
    print(
        f"{name} slot={cal.get('slotDuration')}{cal.get('slotDurationUnit')} "
        f"hours={summarize(cal.get('openHours'))} "
        f"members={json.dumps([{k: m.get(k) for k in ('userId','selected','priority','isPrimary') if k in m} for m in tms], ensure_ascii=False)}"
    )
    if tms:
        print("  raw member0 keys", list(tms[0].keys()))
