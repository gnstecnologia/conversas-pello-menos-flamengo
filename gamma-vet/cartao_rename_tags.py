# -*- coding: utf-8 -*-
"""Renomeia tags para o padrao '{nome} - trafego' e atualiza campo Tag Anuncio."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

ENV = Path(r"c:\Users\GC1\Desktop\Automação GHL\.env")
OUT = Path(r"c:\Users\GC1\Desktop\Automação GHL\gamma-vet")
vals = {}
for line in ENV.read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()

KEY = vals["GHL_CARTAO_TODOS_CG_API_KEY"]
LOC = vals["GHL_CARTAO_TODOS_CG_LOCATION_ID"]
CF_C = "UJkJuWW3JW4gcOU14NLS"
CF_O = "iYKCLDTp0IuIqgFChryY"

# old stored names (GHL lowercase) / old field values -> new
RENAME = [
    {
        "old_tag": "1-só legenda",
        "old_field": "1-Só Legenda",
        "new": "só legenda - trafego",
    },
    {
        "old_tag": "2-coisas com a cdt",
        "old_field": "2-Coisas com a CDT",
        "new": "coisas com a cdt - trafego",
    },
    {
        "old_tag": "3-com a cdt",
        "old_field": "3-Com a CDT",
        "new": "com a cdt - trafego",
    },
    {
        "old_tag": "4-a hora é agora",
        "old_field": "4-A Hora é Agora",
        "new": "a hora é agora - trafego",
    },
    {
        "old_tag": "5-sus",
        "old_field": "5-SUS",
        "new": "sus - trafego",
    },
    {
        "old_tag": "6-ana maria",
        "old_field": "6-ANA MARIA",
        "new": "ana mari - trafego",
    },
]
OLD_TO_NEW = {r["old_field"]: r["new"] for r in RENAME}
OLD_TAG_TO_NEW = {r["old_tag"]: r["new"] for r in RENAME}


def req(method, url, body=None):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    r = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {KEY}",
            "Version": "2021-07-28",
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "Mozilla/5.0",
        },
    )
    for attempt in range(5):
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
            if e.code == 429:
                time.sleep(2 + attempt * 2)
                continue
            return e.code, parsed
        except Exception as ex:
            if attempt < 4:
                time.sleep(1 + attempt)
                continue
            return 0, {"error": str(ex)}
    return 429, {"error": "rate limited"}


def list_tags():
    code, data = req("GET", f"https://services.leadconnectorhq.com/locations/{LOC}/tags")
    tags = (data or {}).get("tags") or []
    return {t.get("name"): t for t in tags}


print("=== create new tags ===")
existing = list_tags()
for r in RENAME:
    if r["new"] in existing:
        print("exists", r["new"])
        continue
    c, b = req("POST", f"https://services.leadconnectorhq.com/locations/{LOC}/tags", {"name": r["new"]})
    print("create", r["new"], c)

applied = json.loads((OUT / "cartao-agosto-applied-detail.json").read_text(encoding="utf-8"))
print("contacts", len(applied))

errors = []
ok_n = 0
for i, lead in enumerate(applied, 1):
    cid = lead["contactId"]
    old_field = lead["tag"]
    new = OLD_TO_NEW.get(old_field)
    if not new:
        errors.append({"contact": cid, "reason": "unknown old tag", "tag": old_field})
        continue
    old_tag = next(r["old_tag"] for r in RENAME if r["old_field"] == old_field)

    c1, b1 = req("POST", f"https://services.leadconnectorhq.com/contacts/{cid}/tags", {"tags": [new]})
    c2, b2 = req(
        "DELETE",
        f"https://services.leadconnectorhq.com/contacts/{cid}/tags",
        {"tags": [old_tag]},
    )
    c3, b3 = req(
        "PUT",
        f"https://services.leadconnectorhq.com/contacts/{cid}",
        {"customFields": [{"id": CF_C, "field_value": new}]},
    )
    opp_ok = []
    for u in (lead.get("opps") or {}).get("updates") or []:
        oid = u.get("id")
        if not oid:
            continue
        body = {"customFields": [{"id": CF_O, "field_value": new}]}
        # pipelineId from previous apply not stored; GET opp if PUT fails
        c4, b4 = req("PUT", f"https://services.leadconnectorhq.com/opportunities/{oid}", body)
        if c4 not in (200, 201):
            og = req("GET", f"https://services.leadconnectorhq.com/opportunities/{oid}")[1]
            opp = (og or {}).get("opportunity") or og or {}
            if opp.get("pipelineId"):
                body["pipelineId"] = opp["pipelineId"]
            c4, b4 = req("PUT", f"https://services.leadconnectorhq.com/opportunities/{oid}", body)
        opp_ok.append(c4)
    if c1 in (200, 201) and c3 in (200, 201) and all(x in (200, 201) for x in opp_ok):
        ok_n += 1
    else:
        errors.append({
            "contact": cid,
            "add": c1,
            "del": c2,
            "cf": c3,
            "opps": opp_ok,
            "add_body": str(b1)[:180],
            "cf_body": str(b3)[:180],
        })
    if i % 20 == 0:
        print("updated", i, "/", len(applied), "ok", ok_n)

print("=== delete old location tags ===")
existing = list_tags()
deleted = []
for r in RENAME:
    t = existing.get(r["old_tag"])
    if not t:
        print("old tag not found", r["old_tag"])
        continue
    c, b = req("DELETE", f"https://services.leadconnectorhq.com/locations/{LOC}/tags/{t['id']}")
    print("delete", r["old_tag"], c)
    deleted.append({"old": r["old_tag"], "code": c})

# live check one
sample = applied[0]
cid = sample["contactId"]
cbody = req("GET", f"https://services.leadconnectorhq.com/contacts/{cid}")[1]
contact = (cbody or {}).get("contact") or {}
oid = ((sample.get("opps") or {}).get("updates") or [{}])[0].get("id")
obody = req("GET", f"https://services.leadconnectorhq.com/opportunities/{oid}")[1] if oid else {}
opp = (obody or {}).get("opportunity") or {}

final_tags = list_tags()
payload = {
    "ok_n": ok_n,
    "errors": errors,
    "deleted": deleted,
    "location_tags_new": [r["new"] for r in RENAME if r["new"] in final_tags or r["new"].lower() in {n.lower() for n in final_tags}],
    "sample_contact_tags": contact.get("tags"),
    "sample_contact_cf": contact.get("customFields"),
    "sample_opp_cf": opp.get("customFields"),
}
(OUT / "cartao-agosto-rename.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print("ok_n", ok_n, "errors", len(errors))
print("saved")
