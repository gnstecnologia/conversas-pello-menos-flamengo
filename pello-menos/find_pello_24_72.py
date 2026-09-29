# -*- coding: utf-8 -*-
"""Acha outbound texto livre com gap 24h–72h após último inbound (CTWA)."""
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ENV = Path(r"c:\Users\GC1\Desktop\Automação GHL\.env")
vals = {}
for line in ENV.read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()
KEY = vals["GHL_PELLO_API_KEY"]
LOC = vals["GHL_PELLO_LOCATION_ID"]
BRT = timezone(timedelta(hours=-3))


def req(path, version="2021-04-15"):
    r = urllib.request.Request(
        "https://services.leadconnectorhq.com" + path,
        headers={
            "Authorization": f"Bearer {KEY}",
            "Version": version,
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
            "Location-Id": LOC,
        },
    )
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            return json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return {"_err": e.code}


def msgs(cid):
    d = req(f"/conversations/{cid}/messages?limit=100")
    m = d.get("messages") or d.get("data") or []
    if isinstance(m, dict):
        m = m.get("messages") or []
    return sorted(m or [], key=lambda x: str(x.get("dateAdded") or ""))


def pdt(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).astimezone(BRT)
    except Exception:
        return None


hits = []
# paginate recent convs
convs = []
d = req(f"/conversations/search?locationId={LOC}&limit=50&sort=desc&sortBy=last_message_date")
convs.extend(d.get("conversations") or [])
print("convs page1", len(convs))

for c in convs:
    cid = c.get("id")
    name = c.get("contactName") or ""
    ms = msgs(cid)
    last_in = None
    last_in_body = ""
    for m in ms:
        mt = m.get("messageType") or ""
        if mt == "TYPE_ACTIVITY_OPPORTUNITY":
            continue
        dt = pdt(m.get("dateAdded"))
        direction = m.get("direction")
        body = (m.get("body") or "").replace("\n", " | ")
        src = m.get("source")
        status = m.get("status")
        if direction == "inbound":
            last_in = dt
            last_in_body = body[:120]
            continue
        if direction != "outbound" or not last_in or not dt:
            continue
        hours = (dt - last_in).total_seconds() / 3600
        if 24 <= hours <= 72 and status in ("delivered", "read", "sent"):
            # skip if looks like named template header
            is_named_tpl = body.startswith("Confirmação de Atendimento") or body.startswith("Seu atendimento")
            hits.append({
                "name": name,
                "cid": cid,
                "hours": round(hours, 1),
                "when": dt.strftime("%d/%m %H:%M"),
                "last_in": last_in.strftime("%d/%m %H:%M"),
                "src": src,
                "status": status,
                "tpl_like": is_named_tpl,
                "out": body[:220],
                "in": last_in_body,
            })
    time.sleep(0.08)

print("\nHITS 24-72h:", len(hits))
# prefer free-form (not named template)
free = [h for h in hits if not h["tpl_like"]]
print("free-form-like:", len(free), "named-tpl-like:", len(hits) - len(free))
for h in free[:15]:
    print("\n---", h["name"], h["hours"], "h", "src="+str(h["src"]), h["status"])
    print("  inbound", h["last_in"], "|", h["in"])
    print("  outbound", h["when"], "|", h["out"])
if not free:
    for h in hits[:8]:
        print("\n(tpl?) ---", h["name"], h["hours"], "h", h["out"][:80])
