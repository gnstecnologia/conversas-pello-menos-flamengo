# -*- coding: utf-8 -*-
"""Dump só Giully + conversas de hoje com oferta de dentista errado."""
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ENV = Path(r"c:\Users\GC1\Desktop\Automação GHL\.env")
OUT = Path(r"c:\Users\GC1\Desktop\Automação GHL\multiodonto-audit")
key = None
for line in ENV.read_text(encoding="utf-8").splitlines():
    if line.startswith("GHL_MULTIODONTO_API_KEY="):
        key = line.split("=", 1)[1].strip()
        break

LOC = "3R4hY0j3TJyj2SkmSQL3"
UA = "Mozilla/5.0"
BRT = timezone(timedelta(hours=-3))
BASE = "https://services.leadconnectorhq.com"

# Giully + today booking-ish
IDS = [
    ("Giully", "Om386aFC5z60v9Xk6ZPO"),
    ("Paula", "akjIeaaqifGPXlY8CQMW"),
    ("Cleide", "O83ngZ0VQ5tuZLaAHHwf"),
    ("Jaque", "4oQ9DzZWa3jFbHIWZVrn"),
    ("Renata Andrade", "eeHSCPPECCEffkMRZTtB"),
    ("Anny Caroline", "K0z1WiYbOjo5w7NOz3OD"),
    ("Natasha Costa", "FaViwcbqim1xBB4kByCI"),
    ("Michele", "54wIxzfoz7hY5XjzJ9Dz"),
    ("Ju", "NGrEWDhGGighHXVtzRrR"),
    ("Flavia", "3bUhiJAM5Wif7kBbSx1A"),
    ("bruno", "XC3HTJAViPN57jvDbzgR"),
    ("coutobiel", "hlN2p8EBHKf2T2mgMMi6"),
    ("monis", "5cWxY9tFslGrSQxOxjPM"),
]


def req(path, ver="2021-04-15"):
    r = urllib.request.Request(
        BASE + path,
        headers={
            "Authorization": f"Bearer {key}",
            "Version": ver,
            "Accept": "application/json",
            "User-Agent": UA,
        },
    )
    for i in range(4):
        try:
            with urllib.request.urlopen(r, timeout=90) as resp:
                return json.loads(resp.read().decode() or "{}")
        except urllib.error.HTTPError as e:
            if e.code in (429, 502) and i < 3:
                time.sleep(2 + i)
                continue
            return {"_err": e.code, "_body": e.read().decode(errors="replace")[:500]}
    return {}


def extract_msgs(payload):
    m = payload.get("messages") or payload.get("data") or []
    if isinstance(m, dict):
        m = m.get("messages") or m.get("data") or []
    return m if isinstance(m, list) else []


dump = {}
for name, cid in IDS:
    payload = req(f"/conversations/{cid}/messages?limit=100")
    msgs = extract_msgs(payload)
    # newest first typically — reverse to chronological
    msgs_sorted = sorted(
        msgs,
        key=lambda x: str(x.get("dateAdded") or x.get("timestamp") or ""),
    )
    print(f"\n========== {name} ({cid}) n={len(msgs_sorted)} ==========")
    lines = []
    for m in msgs_sorted:
        ts = m.get("dateAdded") or ""
        try:
            dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00")).astimezone(BRT)
            tss = dt.strftime("%d/%m %H:%M")
        except Exception:
            tss = str(ts)[:16]
        direction = "PAC" if m.get("direction") == "inbound" else "BOT"
        src = m.get("source") or ""
        if src == "app" and not (m.get("body") or "").strip():
            continue
        body = (m.get("body") or m.get("message") or "").replace("\n", " | ")
        if not body.strip():
            continue
        if "Employee action log" in body:
            continue
        line = f"[{tss}] {direction} | {body}"
        lines.append(line)
        # only print today-ish or last 40 lines
        if dt.date() >= datetime(2026, 8, 31, tzinfo=BRT).date() if "dt" in dir() else True:
            print(line[:400])
    dump[name] = {"id": cid, "lines": lines, "n": len(msgs_sorted)}

(OUT / "audit-hoje-key-convs.json").write_text(
    json.dumps(dump, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("\nWrote audit-hoje-key-convs.json")
