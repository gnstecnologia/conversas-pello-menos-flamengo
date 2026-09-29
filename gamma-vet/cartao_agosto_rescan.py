# -*- coding: utf-8 -*-
"""Re-scan 01/08-18/08/2026, achar leads dos 6 anuncios, tagar faltantes."""
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
TAGS = set(AD_TO_TAG.values())
BRT = timezone(timedelta(hours=-3))
RANGE_START = datetime(2026, 8, 1, 0, 0, 0, tzinfo=BRT)
RANGE_END = datetime(2026, 8, 19, 0, 0, 0, tzinfo=BRT)  # ate fim do dia 18/08

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
    for attempt in range(6):
        try:
            with urllib.request.urlopen(r, timeout=90) as resp:
                raw = resp.read().decode("utf-8")
                return resp.status, json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            err = e.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(err)
            except Exception:
                parsed = err
            if e.code in (429, 502, 503, 504):
                time.sleep(2 + attempt * 2)
                continue
            return e.code, parsed
        except Exception as ex:
            if attempt < 5:
                time.sleep(1 + attempt)
                continue
            return 0, {"error": str(ex)}
    return 429, {"error": "rate limited"}


def parse_dt(s):
    if not s:
        return None
    try:
        if isinstance(s, (int, float)):
            ts = float(s)
            if ts > 1e12:
                ts /= 1000.0
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return None


def in_range(dt):
    if not dt:
        return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return RANGE_START <= dt.astimezone(BRT) < RANGE_END


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


def extract_ad_from_conv(cid, contact_id, fallback_date=None):
    for m in conv_messages(cid):
        body = str(m.get("body") or m.get("message") or "")
        mid = RX_ID.search(body)
        if not mid:
            continue
        ad = mid.group(1)
        if ad not in AD_TO_TAG:
            continue
        dt = parse_dt(m.get("dateAdded") or m.get("timestamp") or fallback_date)
        return ad, AD_TO_TAG[ad], dt
    return None, None, None


def get_contact(cid):
    code, data = req("GET", f"https://services.leadconnectorhq.com/contacts/{cid}")
    return (data or {}).get("contact") or {}


def has_tag(contact, tag):
    tags = [t.lower() for t in (contact.get("tags") or [])]
    return tag.lower() in tags


def get_cf_value(contact, field_id):
    for f in contact.get("customFields") or []:
        if f.get("id") == field_id:
            return f.get("value") or f.get("fieldValue") or f.get("field_value")
    return None


def scan_by_conversations():
    leads = {}
    pages = 0
    start_after = None
    convs_checked = 0
    while pages < 250:
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
            ad, tag, dt = extract_ad_from_conv(cid, contact_id, last_date)
            if not ad:
                continue
            # usar data do contato se mensagem sem data clara
            if not in_range(dt):
                cobj = get_contact(contact_id)
                dt = parse_dt(cobj.get("dateAdded"))
            if not in_range(dt):
                continue
            if contact_id not in leads:
                leads[contact_id] = {
                    "contactId": contact_id,
                    "conv": cid,
                    "ad": ad,
                    "tag": tag,
                    "date": dt.isoformat() if dt else None,
                    "source": "conv_scan",
                }
        if pages % 10 == 0:
            print("conv page", pages, "checked", convs_checked, "leads", len(leads))
        if page_dates and all(d.astimezone(BRT) < RANGE_START for d in page_dates):
            print("conv scan: before Aug 1, stop")
            break
    return leads, convs_checked, pages


def scan_by_ad_search():
    leads = {}
    for ad, tag in AD_TO_TAG.items():
        q = urllib.parse.quote(ad)
        url = f"https://services.leadconnectorhq.com/conversations/search?locationId={LOC}&limit=100&query={q}"
        code, data = req("GET", url, version="2021-04-15")
        convs = (data or {}).get("conversations") or []
        print("ad search", ad, "convs", len(convs), "total", (data or {}).get("total"))
        for c in convs:
            cid = c.get("id")
            contact_id = c.get("contactId") or c.get("contact_id")
            if not cid or not contact_id:
                continue
            ad2, tag2, dt = extract_ad_from_conv(cid, contact_id, c.get("lastMessageDate"))
            if ad2 != ad:
                continue
            if not in_range(dt):
                cobj = get_contact(contact_id)
                dt = parse_dt(cobj.get("dateAdded"))
            if not in_range(dt):
                continue
            leads[contact_id] = {
                "contactId": contact_id,
                "conv": cid,
                "ad": ad,
                "tag": tag,
                "date": dt.isoformat() if dt else None,
                "source": "ad_search",
            }
    return leads


def scan_contacts_by_date():
    """Contatos criados no periodo com meta ads - checar Source ID na conversa."""
    leads = {}
    start_after_id = None
    pages = 0
    while pages < 80:
        pages += 1
        body = {
            "locationId": LOC,
            "pageLimit": 100,
            "filters": [
                {
                    "field": "dateAdded",
                    "operator": "range",
                    "value": [
                        RANGE_START.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
                        (RANGE_END - timedelta(seconds=1)).astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
                    ],
                }
            ],
        }
        if start_after_id:
            body["startAfterId"] = start_after_id
        code, data = req("POST", "https://services.leadconnectorhq.com/contacts/search", body)
        contacts = (data or {}).get("contacts") or []
        if not contacts:
            break
        for c in contacts:
            start_after_id = c.get("id") or start_after_id
            cid = c.get("id")
            if not cid:
                continue
            dt = parse_dt(c.get("dateAdded"))
            if not in_range(dt):
                continue
            # buscar conversa
            code2, sr = req(
                "GET",
                f"https://services.leadconnectorhq.com/conversations/search?locationId={LOC}&contactId={cid}&limit=5",
                version="2021-04-15",
            )
            convs = (sr or {}).get("conversations") or []
            for conv in convs:
                ad, tag, mdt = extract_ad_from_conv(conv.get("id"), cid, conv.get("lastMessageDate"))
                if ad:
                    leads[cid] = {
                        "contactId": cid,
                        "conv": conv.get("id"),
                        "ad": ad,
                        "tag": tag,
                        "date": (mdt or dt).isoformat() if (mdt or dt) else None,
                        "source": "contact_search",
                    }
                    break
        print("contact page", pages, "batch", len(contacts), "ad_leads", len(leads))
        if len(contacts) < 100:
            break
    return leads


def merge(*dicts):
    out = {}
    for d in dicts:
        out.update(d)
    return out


def apply_missing(leads_list):
    missing_tag = []
    missing_field = []
    applied = []
    errors = []
    for lead in leads_list:
        cid = lead["contactId"]
        tag = lead["tag"]
        c = get_contact(cid)
        ok_tag = has_tag(c, tag)
        cf_val = get_cf_value(c, CF_C)
        ok_field = (cf_val or "").lower() == tag.lower()
        if ok_tag and ok_field:
            continue
        if not ok_tag:
            missing_tag.append(cid)
        if not ok_field:
            missing_field.append(cid)
        c1, b1 = req("POST", f"https://services.leadconnectorhq.com/contacts/{cid}/tags", {"tags": [tag]})
        c2, b2 = req(
            "PUT",
            f"https://services.leadconnectorhq.com/contacts/{cid}",
            {"customFields": [{"id": CF_C, "field_value": tag}]},
        )
        opp_updates = []
        code, data = req(
            "GET",
            f"https://services.leadconnectorhq.com/opportunities/search?location_id={LOC}&contact_id={cid}",
        )
        for o in (data or {}).get("opportunities") or []:
            oid = o.get("id")
            if not oid:
                continue
            body = {"customFields": [{"id": CF_O, "field_value": tag}]}
            if o.get("pipelineId"):
                body["pipelineId"] = o["pipelineId"]
            c3, b3 = req("PUT", f"https://services.leadconnectorhq.com/opportunities/{oid}", body)
            opp_updates.append({"id": oid, "code": c3})
        ok = c1 in (200, 201) and c2 in (200, 201)
        if ok:
            applied.append({"contactId": cid, "tag": tag, "ad": lead["ad"]})
        else:
            errors.append({"contactId": cid, "tag_code": c1, "cf_code": c2, "tag_body": str(b1)[:200]})
        time.sleep(0.05)
    return {
        "missing_tag_before": len(missing_tag),
        "missing_field_before": len(missing_field),
        "applied": applied,
        "errors": errors,
    }


def count_tagged_in_range(leads_list):
    by_tag = {t: 0 for t in TAGS}
    tagged_ok = 0
    for lead in leads_list:
        c = get_contact(lead["contactId"])
        tag = lead["tag"]
        if has_tag(c, tag) and (get_cf_value(c, CF_C) or "").lower() == tag.lower():
            tagged_ok += 1
            by_tag[tag] = by_tag.get(tag, 0) + 1
    return tagged_ok, by_tag


if __name__ == "__main__":
    print("Range:", RANGE_START.date(), "to", (RANGE_END - timedelta(days=1)).date())
    conv_leads, n_convs, n_pages = scan_by_conversations()
    ad_leads = scan_by_ad_search()
    try:
        contact_leads = scan_contacts_by_date()
    except Exception as ex:
        print("contact search failed", ex)
        contact_leads = {}
    all_leads = merge(conv_leads, ad_leads, contact_leads)
    leads_list = list(all_leads.values())

    by_ad = {}
    by_tag = {}
    for L in leads_list:
        by_ad[L["ad"]] = by_ad.get(L["ad"], 0) + 1
        by_tag[L["tag"]] = by_tag.get(L["tag"], 0) + 1

    print("TOTAL LEADS FOUND", len(leads_list))
    print("by_ad", json.dumps(by_ad, ensure_ascii=False))
    print("by_tag", json.dumps(by_tag, ensure_ascii=False))

    tagged_ok, tagged_by_tag = count_tagged_in_range(leads_list)
    print("already tagged ok", tagged_ok, "/", len(leads_list))

    result = apply_missing(leads_list)
    tagged_ok2, tagged_by_tag2 = count_tagged_in_range(leads_list)

    payload = {
        "range": {"start": RANGE_START.isoformat(), "end_exclusive": RANGE_END.isoformat()},
        "scan": {
            "conv_pages": n_pages,
            "convs_checked": n_convs,
            "conv_leads": len(conv_leads),
            "ad_search_leads": len(ad_leads),
            "contact_search_leads": len(contact_leads),
            "total_unique": len(leads_list),
        },
        "by_ad": by_ad,
        "by_tag": by_tag,
        "tagged_before": {"ok": tagged_ok, "by_tag": tagged_by_tag},
        "apply": result,
        "tagged_after": {"ok": tagged_ok2, "by_tag": tagged_by_tag2},
        "leads": leads_list,
    }
    (OUT / "cartao-agosto-rescan.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("applied", len(result["applied"]), "errors", len(result["errors"]))
    print("tagged_after", tagged_ok2, "/", len(leads_list))
    print("saved")
