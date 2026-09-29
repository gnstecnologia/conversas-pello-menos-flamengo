# -*- coding: utf-8 -*-
"""Vincula donos nos calendários para o booking do Excel funcionar.
NÃO altera silêncio de conversa (equipe_interna)."""
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
TZ = ZoneInfo("America/Sao_Paulo")

USER_MARCELLO = "LxQOtMzWVhRqNLlWnLCI"
USER_GUSTAVO = "2XSRsWDCgmL11WFIerwr"
USER_RECEPCAO = "kSZcuwcDWLcaEfX9BwEC"

SCH_GUSTAVO = "Y32sCTtstPNuQRI8s0Sn"
SCH_RECEPCAO = "lnGTiZp5BfJ8xoTyLThd"

# Fernanda US fica com Marcello (schedule intercalado já está nele)
ASSIGN = {
    "fernanda": USER_MARCELLO,
    "luciana": USER_RECEPCAO,
    "cintilo": USER_GUSTAVO,
    "radio": USER_GUSTAVO,
    "eco": USER_RECEPCAO,
    "ecg": USER_RECEPCAO,
    "endo": USER_RECEPCAO,
    "prereserva": USER_RECEPCAO,
}


def curl(method, url, data=None, ver="2021-07-28"):
    cmd = [
        "curl.exe", "-s", "-w", "\nHTTP:%{http_code}",
        "-X", method, url,
        "-H", f"Authorization: Bearer {TOKEN}",
        "-H", f"Version: {ver}",
        "-H", "Accept: application/json",
        "-H", "User-Agent: Mozilla/5.0",
    ]
    if data is not None:
        tmp = OUT / "audit" / "req-tm.json"
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


def tm(uid):
    return [{"userId": uid, "priority": 0.5, "selected": True, "isPrimary": True}]


def put_cal(key, uid):
    cid = CAL[key]
    code, body = curl("GET", f"https://services.leadconnectorhq.com/calendars/{cid}")
    cal = json.loads(body).get("calendar") or {} if body.strip().startswith("{") else {}
    before = [m.get("userId") for m in (cal.get("teamMembers") or [])]
    payload = {"name": cal.get("name") or key, "teamMembers": tm(uid)}
    for field in (
        "openHours", "slotDuration", "slotDurationUnit", "slotInterval",
        "slotIntervalUnit", "description", "calendarType",
    ):
        if cal.get(field) is not None:
            payload[field] = cal[field]
    code2, body2 = curl("PUT", f"https://services.leadconnectorhq.com/calendars/{cid}", payload)
    cal2 = json.loads(body2).get("calendar") or {} if body2.strip().startswith("{") else {}
    after = [m.get("userId") for m in (cal2.get("teamMembers") or [])]
    print(f"{key}: {before} -> {after} ({code2})")


def extend_gustavo_hours():
    """Cintilo 15:30 + 90 min = 17:00; deixa até 18:00 por segurança."""
    payload = {
        "name": "Work Hours",
        "timezone": "America/Sao_Paulo",
        "rules": [
            {"type": "wday", "day": d, "intervals": [{"from": "08:00", "to": "18:00"}]}
            for d in ("monday", "tuesday", "wednesday", "thursday", "friday")
        ],
    }
    code, body = curl(
        "PUT",
        f"https://services.leadconnectorhq.com/calendars/schedules/{SCH_GUSTAVO}",
        payload,
        ver="2021-04-15",
    )
    print("Gustavo WH PUT", code)


def assoc(sid, cid, label):
    code, body = curl(
        "PUT",
        f"https://services.leadconnectorhq.com/calendars/schedules/{sid}/associations/{cid}",
        ver="2021-04-15",
    )
    print("assoc", label, code, body[:100].replace("\n", " "))


def verify():
    now = datetime.now(TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    s = int(now.timestamp() * 1000)
    e = int((now + timedelta(days=10)).timestamp() * 1000)
    for key in ("cintilo", "luciana", "fernanda", "rx"):
        code, body = curl(
            "GET",
            f"https://services.leadconnectorhq.com/calendars/{CAL[key]}/free-slots?startDate={s}&endDate={e}",
        )
        data = json.loads(body) if body.strip().startswith("{") else {}
        days = [k for k in data if k != "traceId" and isinstance(data.get(k), dict)]
        total = sum(len((data.get(k) or {}).get("slots") or []) for k in days)
        print(f"slots {key}: days={len(days)} total={total}")
        if key == "cintilo":
            for k in sorted(days)[:4]:
                slots = [x[11:16] for x in ((data.get(k) or {}).get("slots") or [])]
                print(" ", k, slots)


def main():
    print("=== teamMembers ===")
    for key, uid in ASSIGN.items():
        put_cal(key, uid)

    print("=== Gustavo hours + assoc cintilo/radio ===")
    extend_gustavo_hours()
    assoc(SCH_GUSTAVO, CAL["cintilo"], "gustavo->cintilo")
    assoc(SCH_GUSTAVO, CAL["radio"], "gustavo->radio")

    print("=== Recepcao assoc luciana/eco/ecg/endo/prereserva ===")
    for key in ("luciana", "eco", "ecg", "endo", "prereserva"):
        assoc(SCH_RECEPCAO, CAL[key], f"recepcao->{key}")

    print("=== verify slots ===")
    verify()
    print("DONE")


if __name__ == "__main__":
    main()
