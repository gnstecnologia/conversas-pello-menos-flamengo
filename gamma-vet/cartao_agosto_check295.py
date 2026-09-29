# -*- coding: utf-8 -*-
import json
import re
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
ADS = {
    "120248618435700523": "só legenda - trafego",
    "120245782879890523": "coisas com a cdt - trafego",
    "120244183810290523": "com a cdt - trafego",
    "120253509877330523": "a hora é agora - trafego",
    "120253508815200523": "sus - trafego",
    "120253510024870523": "ana mari - trafego",
}
RX = re.compile(r"Source ID:\s*([0-9]+)", re.I)


def req(method, url, body=None, ver="2021-07-28"):
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
    for i in range(5):
        try:
            with urllib.request.urlopen(r, timeout=90) as resp:
                return json.loads(resp.read().decode("utf-8") or "{}")
        except urllib.error.HTTPError as e:
            if e.code in (429, 502, 503) and i < 4:
                time.sleep(2 + i)
                continue
            return {"_err": e.code, "_body": e.read().decode("utf-8", errors="replace")}
        except Exception as ex:
            if i < 4:
                time.sleep(1)
                continue
            return {"_err": str(ex)}
    return {"_err": "timeout"}


def ad_for_contact(cid):
    s = req(
        "GET",
        f"https://services.leadconnectorhq.com/conversations/search?locationId={LOC}&contactId={cid}&limit=5",
        ver="2021-04-15",
    )
    for c in s.get("conversations") or []:
        conv_id = c.get("id")
        if not conv_id:
            continue
        m = req(
            "GET",
            f"https://services.leadconnectorhq.com/conversations/{conv_id}/messages",
            ver="2021-04-15",
        )
        msgs = m.get("messages") or m.get("data") or []
        if isinstance(msgs, dict):
            msgs = msgs.get("messages") or msgs.get("data") or []
        for msg in msgs:
            body = str(msg.get("body") or msg.get("message") or "")
            hit = RX.search(body)
            if hit and hit.group(1) in ADS:
                return hit.group(1), ADS[hit.group(1)]
    return None, None


def has_tag(c, tag):
    return tag.lower() in [t.lower() for t in (c.get("tags") or [])]


def cf(c):
    for f in c.get("customFields") or []:
        if f.get("id") == CF_C:
            return f.get("value")
    return None


page = 1
total_contacts = 0
total_api = None
with6 = 0
tagged_ok = 0
missing = []
by_tag = {}

while page <= 20:
    body = {
        "locationId": LOC,
        "pageLimit": 100,
        "page": page,
        "filters": [
            {
                "field": "dateAdded",
                "operator": "range",
                "value": {"gte": "2026-08-01T03:00:00.000Z", "lte": "2026-08-19T02:59:59.999Z"},
            }
        ],
    }
    d = req("POST", "https://services.leadconnectorhq.com/contacts/search", body)
    if "_err" in d:
        print("page", page, "err", d["_err"])
        break
    if total_api is None:
        total_api = d.get("total")
    batch = d.get("contacts") or []
    if not batch:
        break
    total_contacts += len(batch)
    for c in batch:
        ad, tag = ad_for_contact(c["id"])
        if not ad:
            continue
        with6 += 1
        by_tag[tag] = by_tag.get(tag, 0) + 1
        if has_tag(c, tag) and (cf(c) or "").lower() == tag.lower():
            tagged_ok += 1
        else:
            missing.append((c["id"], tag))
    print("page", page, "batch", len(batch), "total", total_contacts, "with6", with6, "missing", len(missing))
    if len(batch) < 100:
        break
    page += 1

applied = 0
for cid, tag in missing:
    r1 = req("POST", f"https://services.leadconnectorhq.com/contacts/{cid}/tags", {"tags": [tag]})
    r2 = req(
        "PUT",
        f"https://services.leadconnectorhq.com/contacts/{cid}",
        {"customFields": [{"id": CF_C, "field_value": tag}]},
    )
    sr = req("GET", f"https://services.leadconnectorhq.com/opportunities/search?location_id={LOC}&contact_id={cid}")
    for o in sr.get("opportunities") or []:
        oid = o.get("id")
        if oid:
            b = {"customFields": [{"id": CF_O, "field_value": tag}]}
            if o.get("pipelineId"):
                b["pipelineId"] = o["pipelineId"]
            req("PUT", f"https://services.leadconnectorhq.com/opportunities/{oid}", b)
    if "_err" not in r1 and "_err" not in r2:
        applied += 1
    time.sleep(0.03)

out = {
    "total_api": total_api,
    "contacts_processed": total_contacts,
    "with_6_ads": with6,
    "tagged_ok_before": tagged_ok,
    "missing_found": len(missing),
    "applied": applied,
    "by_tag": by_tag,
}
OUT.joinpath("cartao-agosto-check295.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print("FINAL", json.dumps(out, ensure_ascii=False))
