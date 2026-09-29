# -*- coding: utf-8 -*-
import json
import re
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path

ENV = Path(r"c:\Users\GC1\Desktop\Automação GHL\.env")
OUT = Path(r"c:\Users\GC1\Desktop\Automação GHL\gamma-vet")
vals = {}
for line in ENV.read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()

KEY = vals["GHL_EHMEDICAL_API_KEY"]
LOC = vals["GHL_EHMEDICAL_LOCATION_ID"]


def req(url, ver="2021-07-28"):
    r = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {KEY}",
            "Version": ver,
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
        },
    )
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        return {"_err": e.code, "_body": e.read().decode("utf-8", errors="replace")}


# search conversations
q = urllib.parse.quote("financeiro")
d = req(
    f"https://services.leadconnectorhq.com/conversations/search?locationId={LOC}&limit=20&query={q}",
    ver="2021-04-15",
)
convs = d.get("conversations") or []
print("convs with financeiro", len(convs), "total", d.get("total"))
hits = []
for c in convs[:15]:
    cid = c.get("id")
    if not cid:
        continue
    m = req(f"https://services.leadconnectorhq.com/conversations/{cid}/messages", ver="2021-04-15")
    msgs = m.get("messages") or m.get("data") or []
    if isinstance(msgs, dict):
        msgs = msgs.get("messages") or msgs.get("data") or []
    for msg in msgs:
        body = str(msg.get("body") or msg.get("message") or "")
        low = body.lower()
        if "finance" in low or ("@" in body and ("whats" in low or "email" in low or "e-mail" in low)):
            if msg.get("direction") == "outbound" or "financeiro" in low:
                hits.append(
                    {
                        "conv": cid,
                        "dir": msg.get("direction"),
                        "src": msg.get("source"),
                        "date": msg.get("dateAdded"),
                        "text": body[:600],
                    }
                )

# also try knowledge bases
agent = req("https://services.leadconnectorhq.com/conversation-ai/agents/X4ctLzGA1JxYDopKofGa")
a = agent.get("agent") or agent
print("kb ids", a.get("knowledgeBaseIds"))
print("kb triggers", a.get("knowledgeBaseTriggers"))

# list knowledge bases if endpoint exists
for url in [
    f"https://services.leadconnectorhq.com/conversation-ai/knowledge-bases?locationId={LOC}",
    f"https://services.leadconnectorhq.com/locations/{LOC}/customValues",
]:
    x = req(url)
    print("probe", url.split("/")[-1], list(x.keys())[:8] if isinstance(x, dict) else type(x))

(OUT / "ehmedical-financeiro-hits.json").write_text(json.dumps(hits, ensure_ascii=False, indent=2), encoding="utf-8")
print("hits", len(hits))
for h in hits[:8]:
    print("---", h.get("date"), h.get("src"), h.get("dir"))
    print(h["text"][:400])
