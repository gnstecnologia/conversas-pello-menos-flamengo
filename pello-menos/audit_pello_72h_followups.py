# -*- coding: utf-8 -*-
"""Checa follow-ups após 24h: template ou texto livre; MODELO convs; ctwaClid."""
import json
import sys
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ENV = Path(r"c:\Users\GC1\Desktop\Automação GHL\.env")
vals = {}
for line in ENV.read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()

FK = vals["GHL_PELLO_API_KEY"]
FLOC = vals["GHL_PELLO_LOCATION_ID"]
MK = vals["GHL_PELLO_MODELO_API_KEY"]
MLOC = vals["GHL_PELLO_MODELO_LOCATION_ID"]
BRT = timezone(timedelta(hours=-3))


def req(key, path, version="2021-04-15", location_id=None):
    headers = {
        "Authorization": f"Bearer {key}",
        "Version": version,
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0",
    }
    if location_id:
        headers["Location-Id"] = location_id
    r = urllib.request.Request("https://services.leadconnectorhq.com" + path, headers=headers)
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")[:300]


def msgs(key, loc, cid):
    st, payload = req(key, f"/conversations/{cid}/messages?limit=80", location_id=loc)
    m = payload.get("messages") if isinstance(payload, dict) else []
    if isinstance(m, dict):
        m = m.get("messages") or []
    return sorted(m or [], key=lambda x: str(x.get("dateAdded") or ""))


def pdt(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).astimezone(BRT)
    except Exception:
        return None


IDS = [
    ("Jennifer", "f4Ias8OHZBHEYFC0x0bA"),
    ("Andrea aparecida", "d05BopLh8UbNZsMWhreg"),
    ("Ivone", "CCiiswLmeMPbhq0F3KeK"),
    ("Adriana Borges", "OIOdiuGYsHWjai9ETAPU"),
    ("Riglea", "ntgQcyO7tYFAUJG6V0hW"),
    ("Sandra", "4zRn58JR7v3Xa7e4xRyw"),
    ("Julia", "ziiJiQCBPqgdri258oIr"),
    ("Evelyn", "JtZmRb44UwkyZnvDDgFC"),
]

print("=== FOLLOW-UPS vs 24h (Franchising) ===")
for name, cid in IDS:
    ms = msgs(FK, FLOC, cid)
    last_in = None
    print(f"\n----- {name} -----")
    for m in ms:
        if m.get("type") not in (19, "TYPE_WHATSAPP") and m.get("messageType") not in ("TYPE_WHATSAPP", 19):
            if m.get("messageType") == "TYPE_ACTIVITY_OPPORTUNITY":
                continue
        dt = pdt(m.get("dateAdded"))
        direction = m.get("direction")
        body = (m.get("body") or "").replace("\n", " | ")[:110]
        src = m.get("source")
        status = m.get("status")
        tss = dt.strftime("%d/%m %H:%M") if dt else "?"
        gap = ""
        if direction == "outbound" and last_in and dt:
            hours = (dt - last_in).total_seconds() / 3600
            gap = f" | gap={hours:.1f}h desde último inbound"
        print(f" [{tss}] {direction} src={src} st={status}{gap} | {body}")
        if direction == "inbound":
            last_in = dt

print("\n=== MODELO CONVERSAS ===")
st, d = req(MK, f"/conversations/search?locationId={MLOC}&limit=10&sort=desc&sortBy=last_message_date", location_id=MLOC)
print("search", st, type(d))
if isinstance(d, dict):
    convs = d.get("conversations") or []
    print("n", len(convs))
    for c in convs[:8]:
        print(" ", c.get("contactName"), (c.get("lastMessageBody") or "")[:80])

print("\n=== MODELO WORKFLOWS/TEMPLATES ===")
st, wf = req(MK, f"/workflows/?locationId={MLOC}", version="2021-07-28", location_id=MLOC)
print("wf", st, (wf.get("workflows") if isinstance(wf, dict) else wf))
st, t = req(MK, f"/locations/{MLOC}/templates?deleted=false&limit=50&originId={MLOC}&type=whatsapp", version="2021-07-28", location_id=MLOC)
print("wa tpl", st, t if not isinstance(t, dict) else (t.get("totalCount"), len(t.get("templates") or [])))
