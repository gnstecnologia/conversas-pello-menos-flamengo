# -*- coding: utf-8 -*-
"""Cria/atualiza schedule RX+TC com sábado e associa aos calendários (sem mexer na Fernanda US)."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.stdout.reconfigure(encoding="utf-8")

OUT = Path(r"c:\Users\GC1\Desktop\Automação GHL\gamma-vet")
ENV = Path(r"c:\Users\GC1\Desktop\Automação GHL\.env")
vals = {}
for line in ENV.read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()

TOKEN = vals["GHL_GAMMA_API_KEY"]
LOC = vals["GHL_GAMMA_LOCATION_ID"]
CAL = json.loads((OUT / "calendar-ids-live.json").read_text(encoding="utf-8"))
UID = CAL["sharedUserFernanda"]
RX = CAL["rx"]
TOMO = CAL["tomo"]
TZ = ZoneInfo("America/Sao_Paulo")


def curl(method: str, url: str, data=None, version="2021-04-15"):
    cmd = [
        "curl.exe", "-s", "-w", "\nHTTP:%{http_code}",
        "-X", method, url,
        "-H", f"Authorization: Bearer {TOKEN}",
        "-H", f"Version: {version}",
        "-H", "Accept: application/json",
        "-H", "User-Agent: Mozilla/5.0",
    ]
    if data is not None:
        tmp = OUT / "audit" / "req-rx-sat.json"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        cmd += ["-H", "Content-Type: application/json", "--data-binary", f"@{tmp}"]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    body = r.stdout
    code = "?"
    if "HTTP:" in body:
        body, code = body.rsplit("HTTP:", 1)
        code = code.strip()
    return code, body


def wday(day, fr, to):
    return {"type": "wday", "day": day, "intervals": [{"from": fr, "to": to}]}


def search_schedules():
    code, body = curl(
        "GET",
        f"https://services.leadconnectorhq.com/calendars/schedules/search?locationId={LOC}&userId={UID}",
    )
    print("schedules search", code)
    data = json.loads(body) if body.strip().startswith("{") else {}
    for s in data.get("schedules") or []:
        print(
            " -", s.get("id"), "|", s.get("name"),
            "| cals", s.get("calendarIds"),
            "| rules", len(s.get("rules") or []),
        )
    return data.get("schedules") or []


def upsert_rx_schedule():
    name = "RX TC — seg a sex + sabado 8-13"
    rules = [
        wday("monday", "08:00", "18:00"),
        wday("tuesday", "08:00", "18:00"),
        wday("wednesday", "08:00", "18:00"),
        wday("thursday", "08:00", "18:00"),
        wday("friday", "08:00", "18:00"),
        wday("saturday", "08:00", "13:00"),
    ]
    payload = {
        "name": name,
        "timezone": "America/Sao_Paulo",
        "locationId": LOC,
        "userId": UID,
        "calendarIds": [RX, TOMO],
        "rules": rules,
    }
    schedules = search_schedules()
    existing = None
    for s in schedules:
        n = s.get("name") or ""
        if n.startswith("RX TC") or n.startswith("Work Hours") and RX in (s.get("calendarIds") or []):
            existing = s.get("id")
            if n.startswith("RX TC"):
                break
    # prefer exact name
    for s in schedules:
        if (s.get("name") or "").startswith("RX TC"):
            existing = s.get("id")
            break

    if existing:
        print("UPDATE schedule", existing)
        code, body = curl(
            "PUT",
            f"https://services.leadconnectorhq.com/calendars/schedules/{existing}",
            payload,
        )
    else:
        print("CREATE schedule")
        code, body = curl("POST", "https://services.leadconnectorhq.com/calendars/schedules", payload)

    print("schedule upsert", code, body[:350].replace("\n", " "))
    data = json.loads(body) if body.strip().startswith("{") else {}
    sch = data.get("schedule") or data
    sid = sch.get("id") or existing
    print("sid", sid)

    if sid:
        for cid, label in ((RX, "rx"), (TOMO, "tomo")):
            code, body = curl(
                "PUT",
                f"https://services.leadconnectorhq.com/calendars/schedules/{sid}/associations/{cid}",
            )
            print("assoc", label, code, body[:180].replace("\n", " "))

        # persist id
        CAL["rxTomoSaturdayScheduleId"] = sid
        (OUT / "calendar-ids-live.json").write_text(
            json.dumps(CAL, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return sid


def ensure_rx_open_hours():
    code, body = curl("GET", f"https://services.leadconnectorhq.com/calendars/{RX}", version="2021-07-28")
    cal = (json.loads(body).get("calendar") if body.strip().startswith("{") else {}) or {}
    payload = {
        "name": cal.get("name") or "Raio-X",
        "calendarType": cal.get("calendarType") or "service_booking",
        "slotDuration": 30,
        "slotDurationUnit": "mins",
        "slotInterval": 30,
        "slotIntervalUnit": "mins",
        "openHours": [
            {"daysOfTheWeek": [1], "hours": [{"openHour": 8, "openMinute": 30, "closeHour": 18, "closeMinute": 0}]},
            {"daysOfTheWeek": [2], "hours": [{"openHour": 8, "openMinute": 30, "closeHour": 18, "closeMinute": 0}]},
            {"daysOfTheWeek": [3], "hours": [{"openHour": 8, "openMinute": 30, "closeHour": 18, "closeMinute": 0}]},
            {"daysOfTheWeek": [4], "hours": [{"openHour": 8, "openMinute": 30, "closeHour": 18, "closeMinute": 0}]},
            {"daysOfTheWeek": [5], "hours": [{"openHour": 8, "openMinute": 30, "closeHour": 18, "closeMinute": 0}]},
            {"daysOfTheWeek": [6], "hours": [{"openHour": 8, "openMinute": 0, "closeHour": 13, "closeMinute": 0}]},
        ],
        "teamMembers": cal.get("teamMembers")
        or [{"userId": UID, "priority": 0.5, "selected": True, "isPrimary": True}],
    }
    code, body = curl("PUT", f"https://services.leadconnectorhq.com/calendars/{RX}", payload, version="2021-07-28")
    print("rx openHours PUT", code)


def verify_slots():
    now = datetime.now(TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    # find next saturdays
    d = now.date()
    sats = []
    while len(sats) < 3:
        if d.weekday() == 5:
            sats.append(d)
        d += timedelta(days=1)

    s = int(now.timestamp() * 1000)
    e = int((now + timedelta(days=21)).timestamp() * 1000)
    for key, cid in (("rx", RX), ("tomo", TOMO), ("fernanda", CAL["fernanda"])):
        code, body = curl(
            "GET",
            f"https://services.leadconnectorhq.com/calendars/{cid}/free-slots?startDate={s}&endDate={e}",
            version="2021-07-28",
        )
        data = json.loads(body) if body.strip().startswith("{") else {}
        print(f"== {key} ==")
        for day in sats:
            day_s = day.isoformat()
            n = len((data.get(day_s) or {}).get("slots") or [])
            print(f"  {day_s} (sab) slots={n}")


def main():
    print("=== Schedules atuais ===")
    search_schedules()
    print("=== Upsert RX/TC schedule com sabado ===")
    upsert_rx_schedule()
    print("=== Garantir RX openHours ===")
    ensure_rx_open_hours()
    print("=== Verify free-slots ===")
    verify_slots()
    print("DONE RX SAT")


if __name__ == "__main__":
    main()
