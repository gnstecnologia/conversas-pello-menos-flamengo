# -*- coding: utf-8 -*-
import json
import urllib.request
import urllib.error
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
        return e.code, e.read().decode("utf-8", errors="replace")


code, faqs = req(
    f"https://services.leadconnectorhq.com/knowledge-base/faqs?locationId={LOC}&knowledgeBaseId={KB}&limit=100"
)
print("faqs", code)
faq_list = (faqs or {}).get("faqs") or (faqs or {}).get("data") or []
if isinstance(faqs, str):
    print(faqs[:400])
    faq_list = []
print("n faqs", len(faq_list) if isinstance(faq_list, list) else faq_list)

hits = []
for f in faq_list if isinstance(faq_list, list) else []:
    q = str(f.get("question") or "")
    a = str(f.get("answer") or "")
    blob = (q + "\n" + a).lower()
    if any(x in blob for x in ["financ", "email", "e-mail", "@", "whatsapp", "telefone", "whats"]):
        hits.append({"id": f.get("id"), "q": q[:200], "a": a[:800]})

code2, files = req(
    f"https://services.leadconnectorhq.com/knowledge-base/files?locationId={LOC}&knowledgeBaseId={KB}"
)
print("files", code2)
file_list = (files or {}).get("files") or (files or {}).get("data") or []
if isinstance(files, str):
    print(files[:400])
    file_list = []
print("n files", len(file_list) if isinstance(file_list, list) else file_list)
for f in file_list if isinstance(file_list, list) else []:
    print(" file", f.get("id"), f.get("name") or f.get("fileName") or f.get("title"), list(f.keys())[:12])

# also try knowledge-base training data / response sources
for path in [
    f"https://services.leadconnectorhq.com/knowledge-bases/{KB}",
    f"https://services.leadconnectorhq.com/knowledge-base/{KB}",
    f"https://services.leadconnectorhq.com/knowledge-base/{KB}?locationId={LOC}",
]:
    c, b = req(path)
    print("kb get", path.split("/")[-1][:40], c, str(b)[:200] if not isinstance(b, dict) else list(b.keys())[:10])

(OUT / "ehmedical-kb-financeiro.json").write_text(
    json.dumps({"faqs_hits": hits, "faqs_all": faq_list, "files": file_list}, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
print("hits", len(hits))
for h in hits:
    print("---", h["id"])
    print("Q:", h["q"])
    print("A:", h["a"][:500])
