# -*- coding: utf-8 -*-
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

ENV = r"c:\Users\GC1\Desktop\Automação GHL\.env"
vals = {}
with open(ENV, encoding="utf-8") as f:
    for line in f:
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            vals[k.strip()] = v.strip()

KEY = vals["GHL_PELLO_API_KEY"]
LOC = vals["GHL_PELLO_LOCATION_ID"]
AGENT = vals.get("GHL_PELLO_AGENT_ID")
UA = "Mozilla/5.0"
OUT = Path(r"c:\Users\GC1\Desktop\Automação GHL\pello-menos")


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


print("=== AGENT ===")
code, ag = req("GET", f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}", version="2021-07-28")
agent = ag.get("agent", ag) if isinstance(ag, dict) else {}
print("name", agent.get("name"), "mode", agent.get("mode"), "primary", agent.get("isPrimary"))
inst = agent.get("instructions") or ""
print("instructions len", len(inst))
(OUT / "pello-agent-instructions.txt").write_text(inst, encoding="utf-8")
print("--- instructions saved ---")

print("\n=== WORKFLOWS ===")
code, wf = req("GET", f"https://services.leadconnectorhq.com/workflows/?locationId={LOC}")
print("wf", code, list(wf)[:8] if isinstance(wf, dict) else type(wf))
wfs = (wf or {}).get("workflows") or (wf or {}).get("data") or []
print("count", len(wfs) if isinstance(wfs, list) else wfs)
for w in (wfs or [])[:30] if isinstance(wfs, list) else []:
    print(" -", (w.get("id") or ""), (w.get("name") or "").encode("ascii", "replace").decode("ascii"), w.get("status"))

print("\n=== CONVERSATIONS ===")
code, convs = req(
    "GET",
    f"https://services.leadconnectorhq.com/conversations/search?locationId={LOC}&limit=20",
    version="2021-04-15",
)
print("search", code, list(convs)[:10] if isinstance(convs, dict) else str(convs)[:200])
conversations = []
if isinstance(convs, dict):
    conversations = convs.get("conversations") or convs.get("data") or []
print("n convs", len(conversations) if isinstance(conversations, list) else conversations)

# keywords that look like asking for data
keys = ("cpf", "e-mail", "email", "nome", "telefone", "whatsapp", "endereço", "endereco", "cep", "rg", "nascimento", "idade", "cidade", "cnpj", "dados", "cadastro", "preencha")

found = []
for c in conversations[:15] if isinstance(conversations, list) else []:
    cid = c.get("id") or c.get("conversationId")
    last = c.get("lastMessageBody") or c.get("snippet") or ""
    print("\nCONV", cid, "lastType", c.get("lastMessageType"), "dir", c.get("lastMessageDirection"))
    print(" last:", str(last)[:180].replace("\n", " ").encode("ascii", "replace").decode("ascii"))
    if not cid:
        continue
    code, msgs = req("GET", f"https://services.leadconnectorhq.com/conversations/{cid}/messages", version="2021-04-15")
    messages = []
    if isinstance(msgs, dict):
        messages = msgs.get("messages") or msgs.get("data") or []
        if isinstance(messages, dict):
            messages = messages.get("messages") or messages.get("data") or []
    # outbound only
    n_out = 0
    for m in messages if isinstance(messages, list) else []:
        direction = (m.get("direction") or m.get("type") or "")
        body = m.get("body") or m.get("message") or ""
        src = m.get("source") or m.get("type") or ""
        outbound = str(direction).lower() in ("outbound", "out", "2") or m.get("direction") == "outbound"
        if not outbound and m.get("userId"):
            outbound = True
        # GHL often uses type: TYPE_SMS / WhatsApp and direction outbound
        if str(m.get("direction", "")).lower() != "inbound":
            text = str(body)
            low = text.lower()
            if any(k in low for k in keys) and len(text) > 20:
                found.append({
                    "conv": cid,
                    "date": m.get("dateAdded") or m.get("timestamp"),
                    "type": m.get("type"),
                    "direction": m.get("direction"),
                    "source": src,
                    "text": text[:800],
                })
                n_out += 1
    print("  msgs", len(messages) if isinstance(messages, list) else type(messages), "hits", n_out)

print("\n\n===== HITS ASKING DATA =====", len(found))
(OUT / "pello-last-automation-msgs.json").write_text(json.dumps(found, ensure_ascii=False, indent=2), encoding="utf-8")
print("saved", len(found), "hits")
