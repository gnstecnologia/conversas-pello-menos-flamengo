# -*- coding: utf-8 -*-
"""Cria tags + custom fields e aplica nos leads de agosto (Cartao de Todos CG)."""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
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

# Tag padronizada = valor do campo
AD_MAP = {
    "120248618435700523": "1-Só Legenda",
    "120248618435710523": "1-Só Legenda",
    "120245782879890523": "2-Coisas com a CDT",
    "120245782879900523": "2-Coisas com a CDT",
    "120244183810290523": "3-Com a CDT",
    "120244183810310523": "3-Com a CDT",
    "120253509877330523": "4-A Hora é Agora",
    "120253509877310523": "4-A Hora é Agora",
    "120253508815200523": "5-SUS",
    "120253508815210523": "5-SUS",
    "120253510024870523": "6-ANA MARIA",
    "120253510024860523": "6-ANA MARIA",
}
TAGS = [
    "1-Só Legenda",
    "2-Coisas com a CDT",
    "3-Com a CDT",
    "4-A Hora é Agora",
    "5-SUS",
    "6-ANA MARIA",
]
FIELD_NAME = "Tag Anúncio"
BRT = timezone(timedelta(hours=-3))
AUG_START = datetime(2026, 8, 1, 0, 0, 0, tzinfo=BRT)
AUG_END = datetime(2026, 9, 1, 0, 0, 0, tzinfo=BRT)

RX_ID = re.compile(r"Source ID:\s*([0-9]+)", re.I)


def req(method, url, body=None, version="2021-07-28"):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    r = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {KEY}",
            "Version": version,
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


def parse_dt(s):
    if not s:
        return None
    try:
        if isinstance(s, (int, float)):
            # ms timestamp
            ts = float(s)
            if ts > 1e12:
                ts /= 1000.0
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        s = str(s).replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    except Exception:
        return None


def in_august(dt):
    if not dt:
        return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return AUG_START <= dt.astimezone(BRT) < AUG_END


def ensure_tags():
    code, data = req("GET", f"https://services.leadconnectorhq.com/locations/{LOC}/tags")
    existing = {t.get("name") for t in (data or {}).get("tags") or []}
    created = []
    for name in TAGS:
        if name in existing:
            print("tag exists", name)
            continue
        c, body = req("POST", f"https://services.leadconnectorhq.com/locations/{LOC}/tags", {"name": name})
        print("create tag", name, c)
        created.append({"name": name, "code": c, "body": body})
    return created


def find_field(model, name):
    code, data = req(
        "GET", f"https://services.leadconnectorhq.com/locations/{LOC}/customFields?model={model}"
    )
    for f in (data or {}).get("customFields") or []:
        if (f.get("name") or "") == name and (f.get("model") or model) == model:
            return f
    return None


def ensure_field(model):
    found = find_field(model, FIELD_NAME)
    if found:
        print("field exists", model, found.get("id"))
        return found
    c, body = req(
        "POST",
        f"https://services.leadconnectorhq.com/locations/{LOC}/customFields",
        {
            "name": FIELD_NAME,
            "dataType": "TEXT",
            "placeholder": "1-Só Legenda | 2-Coisas com a CDT | ...",
            "model": model,
        },
    )
    print("create field", model, c, str(body)[:300])
    cf = (body or {}).get("customField") or body or {}
    if cf.get("id"):
        return cf
    time.sleep(1)
    return find_field(model, FIELD_NAME) or cf


def conv_messages(cid):
    code, msgs = req(
        "GET",
        f"https://services.leadconnectorhq.com/conversations/{cid}/messages",
        version="2021-04-15",
    )
    messages = []
    if isinstance(msgs, dict):
        messages = msgs.get("messages") or msgs.get("data") or []
        if isinstance(messages, dict):
            messages = messages.get("messages") or messages.get("data") or []
    return messages if isinstance(messages, list) else []


def scan_august():
    leads = {}  # contactId -> {tag, ad, date, conv}
    pages = 0
    start_after = None
    convs_checked = 0
    while pages < 120:
        pages += 1
        url = (
            f"https://services.leadconnectorhq.com/conversations/search"
            f"?locationId={LOC}&limit=20&sort=desc&sortBy=last_message_date"
        )
        if start_after:
            url += f"&startAfterDate={urllib.parse.quote(str(start_after))}"
        code, data = req("GET", url, version="2021-04-15")
        convs = (data or {}).get("conversations") or []
        if not convs:
            print("empty page", pages)
            break
        page_dates = []
        for c in convs:
            cid = c.get("id")
            contact_id = c.get("contactId") or c.get("contact_id")
            last_date = c.get("lastMessageDate") or c.get("dateUpdated")
            if last_date:
                start_after = last_date
                dt_last = parse_dt(last_date)
                if dt_last:
                    page_dates.append(dt_last)
            if not cid or not contact_id:
                continue
            convs_checked += 1
            tag_hit = None
            hit_dt = None
            hit_ad = None
            for m in conv_messages(cid):
                body = str(m.get("body") or m.get("message") or "")
                mid = RX_ID.search(body)
                if not mid:
                    continue
                ad = mid.group(1)
                if ad not in AD_MAP:
                    continue
                dt = parse_dt(m.get("dateAdded") or m.get("timestamp") or last_date)
                if not in_august(dt):
                    continue
                tag_hit = AD_MAP[ad]
                hit_dt = dt.isoformat() if dt else None
                hit_ad = ad
                break
            if tag_hit:
                prev = leads.get(contact_id)
                if not prev:
                    leads[contact_id] = {
                        "contactId": contact_id,
                        "conv": cid,
                        "tag": tag_hit,
                        "ad": hit_ad,
                        "date": hit_dt,
                    }
        filled = len(leads)
        print("page", pages, "convs", convs_checked, "august leads", filled)
        if page_dates and all(d.astimezone(BRT) < AUG_START for d in page_dates):
            print("past August, stop")
            break
    return {"pages": pages, "convs_checked": convs_checked, "leads": list(leads.values())}


def add_tag(contact_id, tag):
    return req("POST", f"https://services.leadconnectorhq.com/contacts/{contact_id}/tags", {"tags": [tag]})


def set_contact_field(contact_id, field_id, value):
    return req(
        "PUT",
        f"https://services.leadconnectorhq.com/contacts/{contact_id}",
        {"customFields": [{"id": field_id, "field_value": value}]},
    )


def set_opp_fields(contact_id, field_id, value):
    results = []
    code, data = req(
        "GET",
        f"https://services.leadconnectorhq.com/opportunities/search?location_id={LOC}&contact_id={contact_id}",
    )
    opps = (data or {}).get("opportunities") or []
    for o in opps:
        oid = o.get("id")
        if not oid:
            continue
        body = {
            "customFields": [{"id": field_id, "field_value": value}],
        }
        if o.get("pipelineId"):
            body["pipelineId"] = o["pipelineId"]
        c, resp = req("PUT", f"https://services.leadconnectorhq.com/opportunities/{oid}", body)
        results.append({"id": oid, "code": c, "ok": c in (200, 201)})
    return {"search_code": code, "n": len(opps), "updates": results}


def apply(leads, contact_field_id, opp_field_id):
    summary = {t: 0 for t in TAGS}
    errors = []
    applied = []
    for i, lead in enumerate(leads, 1):
        cid = lead["contactId"]
        tag = lead["tag"]
        c1, b1 = add_tag(cid, tag)
        c2, b2 = set_contact_field(cid, contact_field_id, tag)
        opp = set_opp_fields(cid, opp_field_id, tag)
        ok = c1 in (200, 201) and c2 in (200, 201)
        if ok:
            summary[tag] += 1
        else:
            errors.append({"contact": cid, "tag": tag, "tag_code": c1, "cf_code": c2, "tag_body": str(b1)[:200], "cf_body": str(b2)[:200]})
        applied.append({
            "contactId": cid,
            "tag": tag,
            "tag_code": c1,
            "contact_field_code": c2,
            "opps": opp,
        })
        if i % 20 == 0:
            print("applied", i, "/", len(leads))
    return {"summary": summary, "errors": errors, "applied": applied}


if __name__ == "__main__":
    print("=== 1) TAGS ===")
    ensure_tags()
    print("=== 2) FIELDS ===")
    f_contact = ensure_field("contact")
    f_opp = ensure_field("opportunity")
    print("contact field", (f_contact or {}).get("id"), "opp field", (f_opp or {}).get("id"))
    if not (f_contact or {}).get("id") or not (f_opp or {}).get("id"):
        raise SystemExit("missing custom field ids")

    print("=== 3) SCAN AUGUST ===")
    scan = scan_august()
    (OUT / "cartao-agosto-leads.json").write_text(json.dumps(scan, ensure_ascii=False, indent=2), encoding="utf-8")
    print("leads", len(scan["leads"]))

    print("=== 4) APPLY ===")
    result = apply(scan["leads"], f_contact["id"], f_opp["id"])
    payload = {
        "field_contact": f_contact,
        "field_opportunity": f_opp,
        "scan": {"pages": scan["pages"], "convs_checked": scan["convs_checked"], "n_leads": len(scan["leads"])},
        "summary": result["summary"],
        "errors": result["errors"],
        "applied_n": len(result["applied"]),
    }
    (OUT / "cartao-agosto-apply.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "cartao-agosto-applied-detail.json").write_text(
        json.dumps(result["applied"], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("SUMMARY", json.dumps(result["summary"], ensure_ascii=False))
    print("errors", len(result["errors"]))
    print("saved")
