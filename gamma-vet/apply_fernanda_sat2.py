# -*- coding: utf-8 -*-
"""Agenda própria da Fernanda: sem quinta; sábados só nas datas intercaladas (22/08 aberto)."""
import json
import urllib.request
import urllib.error
from datetime import date, datetime, timedelta, timezone

ENV = r"c:\Users\GC1\Desktop\Automação GHL\.env"
vals = {}
with open(ENV, encoding="utf-8") as f:
    for line in f:
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            vals[k.strip()] = v.strip()

KEY = vals["GHL_GAMMA_API_KEY"]
LOC = vals["GHL_GAMMA_LOCATION_ID"]
CAL_F = "LuylqTlDWQcpnmeslByJ"
UID = "LxQOtMzWVhRqNLlWnLCI"
UA = "Mozilla/5.0"
TZ = timezone(timedelta(hours=-3))


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
        with urllib.request.urlopen(r, timeout=90) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(err)
        except Exception:
            parsed = err
        return e.code, parsed


def open_saturdays():
    out = []
    d = date(2026, 8, 22)
    end = date(2027, 12, 25)
    on = True
    while d <= end:
        if on:
            out.append(d)
        on = not on
        d += timedelta(days=7)
    return out


def wday(day, fr, to):
    return {"type": "wday", "day": day, "intervals": [{"from": fr, "to": to}]}


def daterule(d, fr, to):
    return {"type": "date", "date": d.isoformat(), "intervals": [{"from": fr, "to": to}]}


def slot_count(day_s):
    start = datetime.fromisoformat(f"{day_s}T00:00:00").replace(tzinfo=TZ)
    s = int(start.timestamp() * 1000)
    e = int((start + timedelta(days=1)).timestamp() * 1000)
    code, sl = req(
        "GET",
        f"https://services.leadconnectorhq.com/calendars/{CAL_F}/free-slots?startDate={s}&endDate={e}",
        version="2021-07-28",
    )
    n = 0
    if isinstance(sl, dict):
        n = len((sl.get(day_s) or {}).get("slots") or [])
    return n


code, data = req(
    "GET",
    f"https://services.leadconnectorhq.com/calendars/schedules/search?locationId={LOC}&userId={UID}",
)
print("schedules", code)
for s in (data or {}).get("schedules") or []:
    print(" -", s.get("id"), s.get("name"), "cals", s.get("calendarIds"), "ndays", len(s.get("rules") or []))

opens = open_saturdays()
rules = [
    wday("monday", "08:00", "18:00"),
    wday("tuesday", "08:00", "18:00"),
    wday("wednesday", "08:00", "18:00"),
    wday("friday", "08:00", "18:00"),
]
for d in opens:
    rules.append(daterule(d, "08:00", "14:00"))

payload = {
    "name": "Fernanda US — sem quinta, sábados intercalados",
    "timezone": "America/Sao_Paulo",
    "locationId": LOC,
    "userId": UID,
    "calendarIds": [CAL_F],
    "rules": rules,
}

# reuse if already created
existing_id = None
for s in (data or {}).get("schedules") or []:
    if s.get("name", "").startswith("Fernanda US"):
        existing_id = s.get("id")
        break

if existing_id:
    print("update schedule", existing_id)
    code, out = req("PUT", f"https://services.leadconnectorhq.com/calendars/schedules/{existing_id}", payload)
else:
    print("create schedule rules", len(rules))
    code, out = req("POST", "https://services.leadconnectorhq.com/calendars/schedules", payload)

print("schedule", code, str(out)[:400] if not isinstance(out, dict) else out.get("message", out.get("schedule", out) if not isinstance(out.get("schedule"), dict) else out["schedule"].get("id")))
sch = (out or {}).get("schedule", out) if isinstance(out, dict) else {}
sid = sch.get("id") or existing_id
print("id", sid, "n_rules", len(sch.get("rules") or []), "cals", sch.get("calendarIds"))

if sid:
    code, assoc = req("PUT", f"https://services.leadconnectorhq.com/calendars/schedules/{sid}/associations/{CAL_F}")
    print("assoc", code, assoc)

print("\n=== SLOTS ===")
for d in [
    date(2026, 8, 20),
    date(2026, 8, 21),
    date(2026, 8, 22),
    date(2026, 8, 29),
    date(2026, 9, 5),
    date(2026, 9, 12),
    date(2026, 9, 19),
]:
    print(d.isoformat(), d.strftime("%a"), slot_count(d.isoformat()))
