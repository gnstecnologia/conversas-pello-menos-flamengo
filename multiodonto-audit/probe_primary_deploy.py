# -*- coding: utf-8 -*-
"""Probe APIs de deploy/primary e GET com locationId."""
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ENV = Path(r"c:\Users\GC1\Desktop\Automação GHL\.env")
key = None
for line in ENV.read_text(encoding="utf-8").splitlines():
    if line.startswith("GHL_MULTIODONTO_API_KEY="):
        key = line.split("=", 1)[1].strip()
        break

AGENT = "3Fzfmx7ViwyD9v16h4DR"
LOC = "3R4hY0j3TJyj2SkmSQL3"
BASE = "https://services.leadconnectorhq.com"
BRT = timezone(timedelta(hours=-3))


def req(method, path, body=None, version="2021-07-28"):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {key}",
        "Version": version,
        "Accept": "application/json",
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": "Mozilla/5.0",
        "Location-Id": LOC,
    }
    request = urllib.request.Request(BASE + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = raw[:300]
        return e.code, parsed
    except Exception as ex:
        return 0, str(ex)[:200]


print("=== GET agent + locationId ===")
for path in [
    f"/conversation-ai/agents/{AGENT}",
    f"/conversation-ai/agents/{AGENT}?locationId={LOC}",
]:
    st, r = req("GET", path)
    if isinstance(r, dict):
        print(path, st, "isPrimary" in r, r.get("isPrimary"), "mode", r.get("mode"), "ch", r.get("channels"))
        print("  keys", sorted(k for k in r.keys() if "prim" in k.lower() or "deploy" in k.lower() or "channel" in k.lower() or k == "mode"))
    else:
        print(path, st, str(r)[:200])

print("\n=== probe deploy/channel endpoints ===")
paths = [
    f"/conversation-ai/agents/{AGENT}/deploy",
    f"/conversation-ai/agents/{AGENT}/channels",
    f"/conversation-ai/agents/{AGENT}/routing",
    f"/conversation-ai/agents/{AGENT}/channel-settings",
    f"/conversation-ai/bot/{AGENT}",
    f"/conversation-ai/bot",
    f"/conversation-ai/bots",
    f"/conversations-ai/agents/{AGENT}",
    f"/conversation-ai/channel-management",
    f"/conversation-ai/channel-management/agents/{AGENT}",
    f"/conversation-ai/deployments?locationId={LOC}",
    f"/conversation-ai/deployments/{AGENT}",
]
for p in paths:
    st, r = req("GET", p)
    snippet = str(r)[:180].replace("\n", " ")
    print(f"GET {st} {p} | {snippet}")

print("\n=== PATCH isPrimary ===")
st, r = req("PATCH", f"/conversation-ai/agents/{AGENT}", {"isPrimary": True, "mode": "auto-pilot", "name": "Letícia IA Agendamento"})
print("PATCH", st, str(r)[:300] if not isinstance(r, dict) else {k: r.get(k) for k in ("isPrimary", "mode", "channels", "message", "error")})

print("\n=== recent convs after 12:00 today ===")
st, d = req("GET", f"/conversations/search?locationId={LOC}&limit=15&sort=desc&sortBy=last_message_date", version="2021-04-15")
print("search", st)
for c in (d.get("conversations") or []) if isinstance(d, dict) else []:
    ts = c.get("lastMessageDate") or 0
    try:
        if isinstance(ts, (int, float)):
            dt = datetime.fromtimestamp(ts / 1000 if ts > 1e12 else ts, tz=BRT)
        else:
            dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00")).astimezone(BRT)
    except Exception:
        dt = None
    print(dt, c.get("contactName"), (c.get("lastMessageBody") or "")[:90])
