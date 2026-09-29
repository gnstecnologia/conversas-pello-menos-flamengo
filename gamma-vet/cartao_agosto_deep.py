# -*- coding: utf-8 -*-
"""Contagem ampla: contatos criados 01-18/08 com Source ID dos 6 anuncios."""
import json, re, time, urllib.request, urllib.error, urllib.parse
from datetime import datetime, timezone, timedelta
from pathlib import Path

ENV = Path(r"c:\Users\GC1\Desktop\Automação GHL\.env")
OUT = Path(r"c:\Users\GC1\Desktop\Automação GHL\gamma-vet")
vals = {k.strip(): v.strip() for k, v in (line.split("=", 1) for line in ENV.read_text(encoding="utf-8").splitlines() if "=" in line and not line.strip().startswith("#"))}
KEY = vals["GHL_CARTAO_TODOS_CG_API_KEY"]
LOC = vals["GHL_CARTAO_TODOS_CG_LOCATION_ID"]
CF_C = "UJkJuWW3JW4gcOU14NLS"
CF_O = "iYKCLDTp0IuIqgFChryY"
AD_TO_TAG = {
    "120248618435700523": "só legenda - trafego",
    "120245782879890523": "coisas com a cdt - trafego",
    "120244183810290523": "com a cdt - trafego",
    "120253509877330523": "a hora é agora - trafego",
    "120253508815200523": "sus - trafego",
    "120253510024870523": "ana mari - trafego",
}
BRT = timezone(timedelta(hours=-3))
START = datetime(2026, 8, 1, tzinfo=BRT)
END = datetime(2026, 8, 19, tzinfo=BRT)
RX = re.compile(r"Source ID:\s*([0-9]+)", re.I)
contact_cache = {}


def req(method, url, body=None, ver="2021-07-28"):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    r = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {KEY}", "Version": ver, "Accept": "application/json",
        "Content-Type": "application/json; charset=utf-8", "User-Agent": "Mozilla/5.0",
    })
    for i in range(5):
        try:
            with urllib.request.urlopen(r, timeout=90) as resp:
                return json.loads(resp.read().decode("utf-8") or "{}")
        except urllib.error.HTTPError as e:
            if e.code in (429, 502, 503) and i < 4:
                time.sleep(2 + i * 2)
                continue
            return {"_err": e.code, "_body": e.read().decode("utf-8", errors="replace")}
        except Exception as ex:
            if i < 4:
                time.sleep(1)
                continue
            return {"_err": str(ex)}
    return {"_err": "timeout"}


def pdt(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return None


def in_range(dt):
    return bool(dt) and START <= dt.astimezone(BRT) < END


def contact(cid):
    if cid not in contact_cache:
        d = req("GET", f"https://services.leadconnectorhq.com/contacts/{cid}")
        contact_cache[cid] = (d.get("contact") or {})
    return contact_cache[cid]


def msgs(conv_id):
    d = req("GET", f"https://services.leadconnectorhq.com/conversations/{conv_id}/messages", ver="2021-04-15")
    m = d.get("messages") or d.get("data") or []
    if isinstance(m, dict):
        m = m.get("messages") or m.get("data") or []
    return m if isinstance(m, list) else []


def ad_from_conv(conv_id):
    for m in msgs(conv_id):
        body = str(m.get("body") or m.get("message") or "")
        hit = RX.search(body)
        if hit and hit.group(1) in AD_TO_TAG:
            return hit.group(1)
    return None


def has_tag(c, tag):
    return tag.lower() in [t.lower() for t in (c.get("tags") or [])]


def cf_val(c):
    for f in c.get("customFields") or []:
        if f.get("id") == CF_C:
            return f.get("value")
    return None


leads = {}
start_after = None
pages = 0
while pages < 200:
    pages += 1
    url = f"https://services.leadconnectorhq.com/conversations/search?locationId={LOC}&limit=20&sort=desc&sortBy=last_message_date"
    if start_after:
        url += f"&startAfterDate={urllib.parse.quote(str(start_after))}"
    d = req("GET", url, ver="2021-04-15")
    convs = d.get("conversations") or []
    if not convs:
        break
    oldest = None
    for c in convs:
        start_after = c.get("lastMessageDate") or c.get("dateUpdated") or start_after
        dt_last = pdt(start_after)
        if dt_last and (oldest is None or dt_last < oldest):
            oldest = dt_last
        cid = c.get("contactId")
        conv_id = c.get("id")
        if not cid or not conv_id or cid in leads:
            continue
        cobj = contact(cid)
        dt_created = pdt(cobj.get("dateAdded"))
        if not in_range(dt_created):
            continue
        ad = ad_from_conv(conv_id)
        if not ad:
            continue
        tag = AD_TO_TAG[ad]
        cobj = contact(cid)
        leads[cid] = {
            "contactId": cid,
            "ad": ad,
            "tag": tag,
            "dateAdded": dt_created.isoformat() if dt_created else None,
            "tagged": has_tag(cobj, tag),
            "field": cf_val(cobj),
        }
    if pages % 20 == 0:
        print("page", pages, "leads", len(leads), "oldest", oldest)
    if oldest and oldest.astimezone(BRT) < datetime(2026, 7, 15, tzinfo=BRT):
        print("stop: convs older than mid-July")
        break

# meta leads created in range (any ad)
meta_created = 0
start_id = None
for pg in range(1, 60):
    body = {"locationId": LOC, "pageLimit": 100, "query": "meta ads"}
    if start_id:
        body["startAfterId"] = start_id
    d = req("POST", "https://services.leadconnectorhq.com/contacts/search", body)
    batch = d.get("contacts") or []
    if not batch:
        break
    for c in batch:
        start_id = c.get("id")
        dt = pdt(c.get("dateAdded"))
        if in_range(dt):
            meta_created += 1
    if len(batch) < 100:
        break

missing = [L for L in leads.values() if not L["tagged"] or (L.get("field") or "").lower() != L["tag"].lower()]
applied = []
errors = []
for L in missing:
    cid = L["contactId"]
    tag = L["tag"]
    r1 = req("POST", f"https://services.leadconnectorhq.com/contacts/{cid}/tags", {"tags": [tag]})
    r2 = req("PUT", f"https://services.leadconnectorhq.com/contacts/{cid}", {"customFields": [{"id": CF_C, "field_value": tag}]})
    sr = req("GET", f"https://services.leadconnectorhq.com/opportunities/search?location_id={LOC}&contact_id={cid}")
    for o in sr.get("opportunities") or []:
        oid = o.get("id")
        if oid:
            body = {"customFields": [{"id": CF_O, "field_value": tag}]}
            if o.get("pipelineId"):
                body["pipelineId"] = o["pipelineId"]
            req("PUT", f"https://services.leadconnectorhq.com/opportunities/{oid}", body)
    ok = "_err" not in r1 and "_err" not in r2
    if ok:
        applied.append(cid)
    else:
        errors.append({"cid": cid, "r1": r1, "r2": r2})
    time.sleep(0.05)

by_ad = {}
by_tag = {}
for L in leads.values():
    by_ad[L["ad"]] = by_ad.get(L["ad"], 0) + 1
    by_tag[L["tag"]] = by_tag.get(L["tag"], 0) + 1

payload = {
    "range": "2026-08-01 to 2026-08-18",
    "total_6ads_by_contact_date": len(leads),
    "meta_ads_contacts_created_in_range_query": meta_created,
    "by_ad": by_ad,
    "by_tag": by_tag,
    "missing_before": len(missing),
    "applied": len(applied),
    "errors": errors,
    "leads": list(leads.values()),
}
OUT.joinpath("cartao-agosto-deep.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print("TOTAL 6ads", len(leads))
print("meta query created in range", meta_created)
print("missing applied", len(applied), "errors", len(errors))
print("by_tag", json.dumps(by_tag, ensure_ascii=False))
