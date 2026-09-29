# -*- coding: utf-8 -*-
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ENV = Path(r"c:\Users\GC1\Desktop\Automação GHL\.env")
OUT = Path(r"c:\Users\GC1\Desktop\Automação GHL\pello-menos")
vals = {}
for line in ENV.read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()

KEY = vals["GHL_PELLO_API_KEY"]
LOC = vals["GHL_PELLO_LOCATION_ID"]
AGENT = "507nJgLKZZnfngaP37sp"
BASE = "https://services.leadconnectorhq.com"


def req(path, ver="2021-07-28"):
    h = {
        "Authorization": f"Bearer {KEY}",
        "Version": ver,
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0",
        "Location-Id": LOC,
    }
    r = urllib.request.Request(BASE + path, headers=h)
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw[:500]


st, ag = req(f"/conversation-ai/agents/{AGENT}")
a = ag.get("data") or ag
actions_out = []
for act in a.get("actions") or []:
    aid = act.get("id")
    st2, d = req(f"/conversation-ai/agents/{AGENT}/actions/{aid}")
    data = d.get("data") or d
    det = data.get("details") or {}
    actions_out.append(
        {
            "id": aid,
            "name": data.get("name"),
            "type": data.get("type"),
            "details": det,
        }
    )
    print("===", data.get("name"), data.get("type"))
    print(json.dumps(det, ensure_ascii=False)[:1500])
    print()

# KB
st, kb = req(f"/knowledge-base/?locationId={LOC}")
print("KB", st, list(kb.keys()) if isinstance(kb, dict) else type(kb))
data = kb.get("data") if isinstance(kb, dict) else None
items = []
if isinstance(data, list):
    items = data
elif isinstance(data, dict):
    items = data.get("knowledgeBases") or data.get("items") or data.get("data") or []
for it in items if isinstance(items, list) else []:
    print("KB item", it.get("id"), it.get("name") or it.get("title"))

# Full thread with contraindicacoes
st, convs = req(
    f"/conversations/search?locationId={LOC}&limit=40&sort=desc&sortBy=last_message_date",
    ver="2021-04-15",
)
thread = None
for c in (convs.get("conversations") or []):
    cid = c.get("id")
    st, msgs = req(f"/conversations/{cid}/messages?limit=80", ver="2021-04-15")
    mraw = msgs.get("messages")
    mlist = (mraw.get("messages") if isinstance(mraw, dict) else mraw) or []
    blob = " ".join((m.get("body") or "") for m in mlist).lower()
    if "contraindica" in blob and "cpf" in blob and "nome" in blob:
        mlist = sorted(mlist, key=lambda m: m.get("dateAdded") or 0)
        thread = {
            "contact": c.get("contactName"),
            "id": cid,
            "messages": [
                {
                    "dir": "OUT" if m.get("direction") == "outbound" else "IN",
                    "body": m.get("body") or "",
                    "type": m.get("type"),
                    "source": m.get("source"),
                }
                for m in mlist
                if (m.get("body") or "").strip()
            ],
        }
        break

(OUT / "pello-franchising-qual-dump.json").write_text(
    json.dumps(
        {
            "agent": {
                "personality": a.get("personality"),
                "goal": a.get("goal"),
                "instructions": a.get("instructions"),
                "mode": a.get("mode"),
            },
            "actions": actions_out,
            "thread": thread,
        },
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)
print("saved dump; thread found:", bool(thread), thread.get("contact") if thread else None)
if thread:
    for m in thread["messages"][:25]:
        print(f"[{m['dir']}]", m["body"][:300].replace("\n", " | "))
