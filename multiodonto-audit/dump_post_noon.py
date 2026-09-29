# -*- coding: utf-8 -*-
import json, sys, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ENV = Path(r"c:\Users\GC1\Desktop\Automação GHL\.env")
key = None
for line in ENV.read_text(encoding="utf-8").splitlines():
    if line.startswith("GHL_MULTIODONTO_API_KEY="):
        key = line.split("=", 1)[1].strip()
        break
H = {
    "Authorization": f"Bearer {key}",
    "Version": "2021-04-15",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0",
    "Location-Id": "3R4hY0j3TJyj2SkmSQL3",
}
BRT = timezone(timedelta(hours=-3))

def get(path, ver=None):
    h = dict(H)
    if ver:
        h["Version"] = ver
    r = urllib.request.Request("https://services.leadconnectorhq.com" + path, headers=h)
    with urllib.request.urlopen(r, timeout=60) as resp:
        return json.loads(resp.read().decode())

# find karaoke + taina + monique
d = get("/conversations/search?locationId=3R4hY0j3TJyj2SkmSQL3&limit=20&sort=desc&sortBy=last_message_date")
want = []
for c in d.get("conversations") or []:
    n = (c.get("contactName") or "").lower()
    if "karaoke" in n or "tain" in n or "monique" in n:
        want.append(c)

for c in want:
    cid = c.get("id")
    print("\n====", c.get("contactName"), cid, "====")
    payload = get(f"/conversations/{cid}/messages?limit=30")
    msgs = payload.get("messages") or payload.get("data") or []
    if isinstance(msgs, dict):
        msgs = msgs.get("messages") or []
    msgs = sorted(msgs, key=lambda x: str(x.get("dateAdded") or ""))
    for m in msgs[-15:]:
        ts = m.get("dateAdded") or ""
        try:
            dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00")).astimezone(BRT)
            tss = dt.strftime("%H:%M")
        except Exception:
            tss = str(ts)[:16]
        role = "PAC" if m.get("direction") == "inbound" else "BOT"
        body = (m.get("body") or "").replace("\n", " | ")[:220]
        if not body or "Employee action" in body:
            continue
        print(f"[{tss}] {role} | {body}")
