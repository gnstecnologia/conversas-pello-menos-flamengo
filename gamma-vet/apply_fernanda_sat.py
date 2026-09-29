# -*- coding: utf-8 -*-
"""Sábados intercalados da Dra. Fernanda: 22/08 aberto, 29/08 fechado, e segue."""
import json
import urllib.request
import urllib.error
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ENV = Path(r"c:\Users\GC1\Desktop\Automação GHL\.env")
vals = {}
for line in ENV.read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()

KEY = vals["GHL_GAMMA_API_KEY"]
LOC = vals["GHL_GAMMA_LOCATION_ID"]
CAL_F = "LuylqTlDWQcpnmeslByJ"
UID = "LxQOtMzWVhRqNLlWnLCI"
SID = "qFMZOj1GjAfLRsORSMj7"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
TZ = timezone(timedelta(hours=-3))
BLOCK_TITLE = "Folga Fernanda — sábado intercalado"


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
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(err)
        except Exception:
            parsed = err
        return e.code, parsed


def hours(days, oh, om, ch, cm):
    return [
        {
            "daysOfTheWeek": [d],
            "hours": [{"openHour": oh, "openMinute": om, "closeHour": ch, "closeMinute": cm}],
        }
        for d in days
    ]


def merge(*blocks):
    by_day = {}
    for block in blocks:
        for entry in block:
            for d in entry["daysOfTheWeek"]:
                by_day.setdefault(d, []).extend(entry["hours"])
    return [{"daysOfTheWeek": [d], "hours": hs} for d, hs in sorted(by_day.items())]


def tm():
    return [
        {
            "priority": 0.5,
            "selected": True,
            "userId": UID,
            "isPrimary": True,
            "isZoomAdded": "false",
            "locationConfigurations": [
                {"kind": "custom", "location": "", "position": 0, "zoomOauthId": "", "meetingId": "custom_0"}
            ],
        }
    ]


def saturdays():
    """22/08 aberto, 29/08 fechado, até dez/2027."""
    open_s, closed_s = [], []
    d = date(2026, 8, 22)
    end = date(2027, 12, 25)
    on = True
    while d <= end:
        (open_s if on else closed_s).append(d)
        on = not on
        d += timedelta(days=7)
    return open_s, closed_s


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


open_sats, closed_sats = saturdays()
print("abertos", len(open_sats), "ex:", [x.isoformat() for x in open_sats[:4]])
print("fechados", len(closed_sats), "ex:", [x.isoformat() for x in closed_sats[:4]])

# 1) Work Hours: sábado até 14h (clínica)
print("\n=== Work Hours sábado 08-14 ===")
code, sch = req("GET", f"https://services.leadconnectorhq.com/calendars/schedules/{SID}")
sch = sch.get("schedule", sch) if isinstance(sch, dict) else {}
rules = []
for r in sch.get("rules") or []:
    if r.get("day") == "saturday":
        rules.append({"type": "wday", "day": "saturday", "intervals": [{"from": "08:00", "to": "14:00"}]})
    else:
        rules.append(r)
if not any(r.get("day") == "saturday" for r in rules):
    rules.append({"type": "wday", "day": "saturday", "intervals": [{"from": "08:00", "to": "14:00"}]})
code, out = req(
    "PUT",
    f"https://services.leadconnectorhq.com/calendars/schedules/{SID}",
    {"name": "Work Hours", "timezone": "America/Sao_Paulo", "rules": rules},
)
print("schedule", code, [r.get("day") for r in ((out.get("schedule", out) or {}).get("rules") or [])])

# 2) Fernanda: seg-qua+sex 8:30-18 + sábado 8-14 (sem quinta)
print("\n=== PUT Fernanda openHours ===")
oh = merge(hours([1, 2, 3, 5], 8, 30, 18, 0), hours([6], 8, 0, 14, 0))
code, body = req(
    "PUT",
    f"https://services.leadconnectorhq.com/calendars/{CAL_F}",
    {
        "openHours": oh,
        "slotDuration": 30,
        "slotDurationUnit": "mins",
        "slotInterval": 30,
        "slotIntervalUnit": "mins",
        "teamMembers": tm(),
        "isActive": True,
        "description": (
            "Ultrassonografia Dra. Fernanda. Seg/ter/qua/sex 8:30-18:00. NÃO atende quinta. "
            "Sábados intercalados: 22/08/2026 aberto, 29/08/2026 fechado, e assim por diante. Sábado 8:00-14:00."
        ),
    },
)
cal = body.get("calendar", body) if isinstance(body, dict) else {}
print(
    "PUT",
    code,
    "days",
    [x.get("daysOfTheWeek") for x in (cal.get("openHours") or [])],
    "user",
    [m.get("userId") for m in (cal.get("teamMembers") or [])],
)

# 3) bloquear sábados fechados
print("\n=== block slots ===")
start_ms = int(datetime(2026, 8, 22, tzinfo=TZ).timestamp() * 1000)
end_ms = int(datetime(2027, 12, 26, tzinfo=TZ).timestamp() * 1000)
code, existing = req(
    "GET",
    f"https://services.leadconnectorhq.com/calendars/blocked-slots?locationId={LOC}&calendarId={CAL_F}&startTime={start_ms}&endTime={end_ms}",
)
blocks = (existing or {}).get("events") or (existing or {}).get("blockedSlots") or []
if isinstance(existing, dict) and not blocks:
    for k, v in existing.items():
        if isinstance(v, list) and v and isinstance(v[0], dict):
            blocks = v
            break
print("existing blocks", len(blocks) if isinstance(blocks, list) else type(blocks), "keys", list(existing)[:8] if isinstance(existing, dict) else existing)
already = set()
for b in blocks if isinstance(blocks, list) else []:
    st = str(b.get("startTime") or "")
    if BLOCK_TITLE in str(b.get("title") or ""):
        already.add(st[:10])

created = skipped = failed = 0
for d in closed_sats:
    if d.isoformat() in already:
        skipped += 1
        continue
    start = datetime(d.year, d.month, d.day, 8, 0, tzinfo=TZ)
    end = datetime(d.year, d.month, d.day, 14, 0, tzinfo=TZ)
    code, body = req(
        "POST",
        "https://services.leadconnectorhq.com/calendars/events/block-slots",
        {
            "title": BLOCK_TITLE,
            "calendarId": CAL_F,
            "locationId": LOC,
            "startTime": start.isoformat(),
            "endTime": end.isoformat(),
        },
    )
    if str(code).startswith("2"):
        created += 1
    else:
        failed += 1
        if failed <= 3:
            print("FAIL", d, code, str(body)[:250])
print("created", created, "skipped", skipped, "failed", failed)

print("\n=== SLOTS Fernanda ===")
for d in [
    date(2026, 8, 20),  # qui — 0
    date(2026, 8, 21),  # sex — >0
    date(2026, 8, 22),  # sáb ABERTO
    date(2026, 8, 29),  # sáb FECHADO
    date(2026, 9, 5),   # sáb ABERTO
    date(2026, 9, 12),  # sáb FECHADO
    date(2026, 9, 19),  # sáb ABERTO
]:
    n = slot_count(d.isoformat())
    print(d.isoformat(), d.strftime("%a"), n)
