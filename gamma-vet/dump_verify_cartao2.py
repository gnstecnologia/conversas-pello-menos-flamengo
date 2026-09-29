# -*- coding: utf-8 -*-
import json
import urllib.request
from pathlib import Path

ENV = Path(r"c:\Users\GC1\Desktop\Automação GHL\.env")
vals = {}
for line in ENV.read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()
KEY = vals["GHL_CARTAO_TODOS_CG_API_KEY"]
CF_C = "UJkJuWW3JW4gcOU14NLS"
CF_O = "iYKCLDTp0IuIqgFChryY"
OUT = Path(r"c:\Users\GC1\Desktop\Automação GHL\gamma-vet")
applied = json.loads((OUT / "cartao-agosto-applied-detail.json").read_text(encoding="utf-8"))


def get(url):
    r = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {KEY}",
        "Version": "2021-07-28",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0",
    })
    with urllib.request.urlopen(r, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))

# one sample per tag
seen = {}
for a in applied:
    seen.setdefault(a["tag"], a)

samples = []
for tag, a in seen.items():
    cid = a["contactId"]
    oid = (a.get("opps") or {}).get("updates", [{}])[0].get("id")
    c = get(f"https://services.leadconnectorhq.com/contacts/{cid}").get("contact") or {}
    o = get(f"https://services.leadconnectorhq.com/opportunities/{oid}").get("opportunity") or {} if oid else {}
    cval = None
    for f in c.get("customFields") or []:
        if f.get("id") == CF_C:
            cval = f.get("value")
    oval = None
    for f in o.get("customFields") or []:
        if f.get("id") == CF_O:
            oval = f.get("fieldValue") or f.get("value")
    samples.append({
        "tag_expected": tag,
        "contactId": cid,
        "contact_tags": c.get("tags"),
        "contact_field": cval,
        "oppId": oid,
        "opp_tags": o.get("tags"),
        "opp_field": oval,
        "opp_keys": list(o.keys())[:30],
    })

n_opp = sum(1 for a in applied if (a.get("opps") or {}).get("n", 0) > 0)
payload = {
    "n_applied": len(applied),
    "n_with_opp": n_opp,
    "samples": samples,
}
(OUT / "cartao-agosto-verify2.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print("ok")
