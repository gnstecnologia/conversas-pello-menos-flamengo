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
LOC = vals["GHL_CARTAO_TODOS_CG_LOCATION_ID"]
CF_C = "UJkJuWW3JW4gcOU14NLS"
CF_O = "iYKCLDTp0IuIqgFChryY"
TAGS = ["1-Só Legenda", "2-Coisas com a CDT", "3-Com a CDT", "4-A Hora é Agora", "5-SUS", "6-ANA MARIA"]


def get(url, version="2021-07-28"):
    r = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {KEY}",
        "Version": version,
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0",
    })
    with urllib.request.urlopen(r, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


# tags
tags = [t.get("name") for t in get(f"https://services.leadconnectorhq.com/locations/{LOC}/tags").get("tags") or []]
print("TAGS IN ACCOUNT:")
for t in TAGS:
    print(" ", t, "YES" if t in tags else "MISSING")

# fields
for model in ("contact", "opportunity"):
    fields = get(f"https://services.leadconnectorhq.com/locations/{LOC}/customFields?model={model}").get("customFields") or []
    hit = [f for f in fields if f.get("name") == "Tag Anúncio"]
    print("FIELD", model, hit[0].get("id") if hit else "MISSING")

applied = json.loads(Path(r"c:\Users\GC1\Desktop\Automação GHL\gamma-vet\cartao-agosto-applied-detail.json").read_text(encoding="utf-8"))
no_opp = [a for a in applied if a.get("opps", {}).get("n", 0) == 0]
fail_opp = [u for a in applied for u in a.get("opps", {}).get("updates") or [] if not u.get("ok")]
print("applied", len(applied), "no_opp", len(no_opp), "fail_opp", len(fail_opp))

# live sample one per tag
seen = {}
for a in applied:
    seen.setdefault(a["tag"], a)

print("\nLIVE SAMPLES:")
for tag, a in seen.items():
    cid = a["contactId"]
    c = get(f"https://services.leadconnectorhq.com/contacts/{cid}").get("contact") or {}
    ctags = c.get("tags") or []
    cfs = c.get("customFields") or []
    val = None
    for f in cfs:
        if f.get("id") == CF_C or f.get("fieldKey") == "contact.tag_anncio":
            val = f.get("value") or f.get("fieldValue") or f.get("field_value")
    print(" contact", cid, "tag_ok", tag in ctags, "field", val)

    oid = (a.get("opps", {}).get("updates") or [{}])[0].get("id")
    if oid:
        o = get(f"https://services.leadconnectorhq.com/opportunities/{oid}").get("opportunity") or {}
        oval = None
        for f in o.get("customFields") or []:
            if f.get("id") == CF_O or "tag_anncio" in str(f.get("key") or f.get("fieldKey") or ""):
                oval = f.get("fieldValue") or f.get("value") or f.get("field_value")
        print("  opp", oid, "field", oval)
