# -*- coding: utf-8 -*-
import json
import re
import urllib.error
import urllib.parse
import urllib.request
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
KB = "jMVYm98Ii5UA46yb9spC"


def req(url, method="GET", body=None, ver="2021-07-28"):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    r = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {KEY}",
            "Version": ver,
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "Mozilla/5.0",
        },
    )
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8", errors="replace") or "{}")


c, kb = req(f"https://services.leadconnectorhq.com/knowledge-base/{KB}?locationId={LOC}")
(OUT / "ehmedical-kb-raw.json").write_text(json.dumps(kb, ensure_ascii=False, indent=2), encoding="utf-8")
print("kb keys", list(kb.keys()) if isinstance(kb, dict) else type(kb))
data = (kb or {}).get("data") or kb
print("data keys", list(data.keys())[:30] if isinstance(data, dict) else type(data))
# dump nested sources
blob = json.dumps(kb, ensure_ascii=False)
for term in ["financ", "@", "whatsapp", "email", "telefone", "financeiro"]:
    print(term, blob.lower().count(term.lower()))

# Search more conversations: query email / financeiro outbound
hits = []
for q in ["financeiro", "financeiro@", "@ehmedical", "setor financeiro", "departamento financeiro"]:
    d = req(
        f"https://services.leadconnectorhq.com/conversations/search?locationId={LOC}&limit=50&query={urllib.parse.quote(q)}",
        ver="2021-04-15",
    )[1]
    for conv in d.get("conversations") or []:
        cid = conv.get("id")
        m = req(f"https://services.leadconnectorhq.com/conversations/{cid}/messages", ver="2021-04-15")[1]
        msgs = m.get("messages") or m.get("data") or []
        if isinstance(msgs, dict):
            msgs = msgs.get("messages") or msgs.get("data") or []
        for msg in msgs:
            if str(msg.get("direction")).lower() != "outbound":
                continue
            body = str(msg.get("body") or "")
            low = body.lower()
            if ("financ" in low or "@" in body) and ("whats" in low or "email" in low or "e-mail" in low or "@" in body):
                hits.append({"q": q, "conv": cid, "src": msg.get("source"), "date": msg.get("dateAdded"), "text": body[:900]})

# Also scan recent convs for outbound with @ and whatsapp
start = None
for page in range(1, 8):
    url = f"https://services.leadconnectorhq.com/conversations/search?locationId={LOC}&limit=20&sort=desc&sortBy=last_message_date"
    if start:
        url += f"&startAfterDate={urllib.parse.quote(str(start))}"
    d = req(url, ver="2021-04-15")[1]
    convs = d.get("conversations") or []
    if not convs:
        break
    for conv in convs:
        start = conv.get("lastMessageDate") or start
        cid = conv.get("id")
        m = req(f"https://services.leadconnectorhq.com/conversations/{cid}/messages", ver="2021-04-15")[1]
        msgs = m.get("messages") or m.get("data") or []
        if isinstance(msgs, dict):
            msgs = msgs.get("messages") or msgs.get("data") or []
        for msg in msgs:
            if str(msg.get("direction")).lower() != "outbound":
                continue
            body = str(msg.get("body") or "")
            low = body.lower()
            if "financ" in low and ("@" in body or "whats" in low or re.search(r"\d{4,5}[- ]?\d{4}", body)):
                hits.append({"q": "recent", "conv": cid, "src": msg.get("source"), "date": msg.get("dateAdded"), "text": body[:900]})
    print("page", page, "hits", len(hits))

# custom values
cv = req(f"https://services.leadconnectorhq.com/locations/{LOC}/customValues")[1]
cvs = cv.get("customValues") or []
cv_hits = [x for x in cvs if any(t in json.dumps(x, ensure_ascii=False).lower() for t in ["financ", "email", "whats"])]
print("customValues", len(cvs), "hits", len(cv_hits))

(OUT / "ehmedical-financeiro-outbound.json").write_text(
    json.dumps({"hits": hits, "custom_values": cv_hits, "kb_data_keys": list(data.keys()) if isinstance(data, dict) else None}, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
print("saved hits", len(hits))
