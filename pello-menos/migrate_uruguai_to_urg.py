# -*- coding: utf-8 -*-
"""Migra contatos + oportunidades: Pello Menos - Uruguai (antiga) -> Pello Menos - URG."""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ENV = Path(r"c:\Users\GC1\Desktop\Automação GHL\.env")
OUT = Path(r"c:\Users\GC1\Desktop\Automação GHL\pello-menos\urg-migrate-result.json")
vals = {}
for line in ENV.read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()

OLD_K = vals["GHL_PELLO_URUGUAI_OLD_API_KEY"]
OLD_L = vals["GHL_PELLO_URUGUAI_OLD_LOCATION_ID"]
NEW_K = vals["GHL_PELLO_URG_API_KEY"]
NEW_L = vals["GHL_PELLO_URG_LOCATION_ID"]


def req(token: str, method: str, url: str, body=None, ver: str = "2021-07-28"):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {token}",
        "Version": ver,
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0",
    }
    if body is not None:
        headers["Content-Type"] = "application/json; charset=utf-8"
    r = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(r, timeout=90) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw


def get_pipelines(token: str, loc: str):
    st, d = req(token, "GET", f"https://services.leadconnectorhq.com/opportunities/pipelines?locationId={loc}")
    return d.get("pipelines") or []


def build_pipe_map(old_pipes, new_pipes):
    """Map old pipelineId/stageId -> new by pipeline name + stage name."""
    new_by_name = {p.get("name"): p for p in new_pipes}
    pipe_map = {}
    stage_map = {}
    for op in old_pipes:
        np = new_by_name.get(op.get("name"))
        if not np:
            continue
        pipe_map[op["id"]] = np["id"]
        new_stages = {s.get("name"): s.get("id") for s in (np.get("stages") or [])}
        for s in op.get("stages") or []:
            nid = new_stages.get(s.get("name"))
            if nid:
                stage_map[s["id"]] = nid
    return pipe_map, stage_map


def fetch_all_contacts(token: str, loc: str):
    contacts = []
    page = 1
    while True:
        st, d = req(
            token,
            "POST",
            "https://services.leadconnectorhq.com/contacts/search",
            {"locationId": loc, "page": page, "pageLimit": 100},
        )
        batch = d.get("contacts") or []
        contacts.extend(batch)
        total = d.get("total") or 0
        if not batch or len(contacts) >= total:
            break
        page += 1
        if page > 50:
            break
    return contacts


def fetch_all_opps(token: str, loc: str):
    st, d = req(
        token,
        "POST",
        "https://services.leadconnectorhq.com/opportunities/search",
        {"locationId": loc, "limit": 100},
    )
    return d.get("opportunities") or [], d.get("total")


def index_new_contacts(token: str, loc: str):
    """Index existing NEW contacts by phone/email to avoid dupes."""
    by_phone, by_email = {}, {}
    for c in fetch_all_contacts(token, loc):
        ph = (c.get("phone") or "").strip()
        em = (c.get("email") or "").strip().lower()
        if ph:
            by_phone[ph] = c.get("id")
        if em:
            by_email[em] = c.get("id")
    return by_phone, by_email


def create_contact(token: str, loc: str, src: dict):
    body = {
        "locationId": loc,
        "firstName": src.get("firstName") or "",
        "lastName": src.get("lastName") or "",
        "name": src.get("contactName") or src.get("name") or "",
        "email": src.get("email") or None,
        "phone": src.get("phone") or None,
        "address1": src.get("address") or None,
        "city": src.get("city") or None,
        "state": src.get("state") or None,
        "postalCode": src.get("postalCode") or None,
        "country": src.get("country") or None,
        "website": src.get("website") or None,
        "companyName": src.get("companyName") or src.get("businessName") or None,
        "tags": src.get("tags") or [],
        "source": src.get("source") or "migrate-uruguai-antiga",
    }
    # drop empty None-ish
    body = {k: v for k, v in body.items() if v not in (None, "", [])}
    body["locationId"] = loc
    if src.get("tags"):
        body["tags"] = src["tags"]
    st, d = req(token, "POST", "https://services.leadconnectorhq.com/contacts/", body)
    if st in (200, 201):
        c = d.get("contact") or d
        return True, c.get("id"), None
    # duplicate?
    msg = json.dumps(d, ensure_ascii=False) if not isinstance(d, str) else d
    return False, None, f"{st} {msg[:400]}"


def create_opportunity(token: str, loc: str, src: dict, new_contact_id: str, pipe_map: dict, stage_map: dict):
    old_pipe = src.get("pipelineId")
    old_stage = src.get("pipelineStageId")
    new_pipe = pipe_map.get(old_pipe)
    new_stage = stage_map.get(old_stage)
    if not new_pipe:
        return False, None, f"pipeline nao mapeado {old_pipe}"
    if not new_stage:
        # fallback first stage of mapped pipeline
        return False, None, f"stage nao mapeado {old_stage}"
    status = src.get("status") or "open"
    if status not in ("open", "won", "lost", "abandoned"):
        status = "open"
    body = {
        "locationId": loc,
        "pipelineId": new_pipe,
        "pipelineStageId": new_stage,
        "contactId": new_contact_id,
        "name": src.get("name") or "Oportunidade",
        "status": status,
        "monetaryValue": src.get("monetaryValue") or 0,
        "source": src.get("source") or "migrate-uruguai-antiga",
    }
    st, d = req(token, "POST", "https://services.leadconnectorhq.com/opportunities/", body)
    if st in (200, 201):
        o = d.get("opportunity") or d
        return True, o.get("id"), None
    msg = json.dumps(d, ensure_ascii=False) if not isinstance(d, str) else d
    return False, None, f"{st} {msg[:400]}"


def main():
    print("OLD", OLD_L, "-> NEW", NEW_L)
    old_pipes = get_pipelines(OLD_K, OLD_L)
    new_pipes = get_pipelines(NEW_K, NEW_L)
    pipe_map, stage_map = build_pipe_map(old_pipes, new_pipes)
    print("pipe map", len(pipe_map), "stage map", len(stage_map))

    old_contacts = fetch_all_contacts(OLD_K, OLD_L)
    old_opps, opp_total = fetch_all_opps(OLD_K, OLD_L)
    print("source contacts", len(old_contacts), "opps", len(old_opps), "/", opp_total)

    by_phone, by_email = index_new_contacts(NEW_K, NEW_L)
    print("dest already", len(by_phone), "phones", len(by_email), "emails")

    id_map = {}
    contact_results = []
    for i, c in enumerate(old_contacts, 1):
        oid = c.get("id")
        ph = (c.get("phone") or "").strip()
        em = (c.get("email") or "").strip().lower()
        if ph and ph in by_phone:
            id_map[oid] = by_phone[ph]
            contact_results.append({"old": oid, "new": by_phone[ph], "status": "reuse_phone"})
            print(f"[{i}/{len(old_contacts)}] reuse phone", ph, "->", by_phone[ph])
            continue
        if em and em in by_email:
            id_map[oid] = by_email[em]
            contact_results.append({"old": oid, "new": by_email[em], "status": "reuse_email"})
            print(f"[{i}/{len(old_contacts)}] reuse email", em, "->", by_email[em])
            continue
        ok, nid, err = create_contact(NEW_K, NEW_L, c)
        if ok:
            id_map[oid] = nid
            if ph:
                by_phone[ph] = nid
            if em:
                by_email[em] = nid
            contact_results.append({"old": oid, "new": nid, "status": "created"})
            print(f"[{i}/{len(old_contacts)}] created", c.get("contactName") or c.get("firstName"), nid)
        else:
            contact_results.append({"old": oid, "new": None, "status": "error", "error": err})
            print(f"[{i}/{len(old_contacts)}] ERR", err)
        time.sleep(0.15)

    opp_results = []
    for i, o in enumerate(old_opps, 1):
        ocid = o.get("contactId") or ((o.get("contact") or {}).get("id"))
        ncid = id_map.get(ocid)
        if not ncid:
            opp_results.append({"old": o.get("id"), "status": "skip_no_contact", "oldContact": ocid})
            print(f"[opp {i}/{len(old_opps)}] skip no contact map", o.get("name"))
            continue
        ok, nid, err = create_opportunity(NEW_K, NEW_L, o, ncid, pipe_map, stage_map)
        if ok:
            opp_results.append({"old": o.get("id"), "new": nid, "status": "created"})
            print(f"[opp {i}/{len(old_opps)}] created", o.get("name"), nid)
        else:
            opp_results.append({"old": o.get("id"), "status": "error", "error": err})
            print(f"[opp {i}/{len(old_opps)}] ERR", err)
        time.sleep(0.15)

    # final counts
    st, d = req(NEW_K, "POST", "https://services.leadconnectorhq.com/contacts/search", {"locationId": NEW_L, "pageLimit": 1})
    st2, d2 = req(NEW_K, "POST", "https://services.leadconnectorhq.com/opportunities/search", {"locationId": NEW_L, "limit": 1})
    summary = {
        "contacts_created": sum(1 for x in contact_results if x["status"] == "created"),
        "contacts_reused": sum(1 for x in contact_results if x["status"].startswith("reuse")),
        "contacts_error": sum(1 for x in contact_results if x["status"] == "error"),
        "opps_created": sum(1 for x in opp_results if x["status"] == "created"),
        "opps_error": sum(1 for x in opp_results if x["status"] == "error"),
        "opps_skip": sum(1 for x in opp_results if x["status"].startswith("skip")),
        "new_total_contacts": d.get("total") if isinstance(d, dict) else None,
        "new_total_opps": d2.get("total") if isinstance(d2, dict) else None,
        "contact_results": contact_results,
        "opp_results": opp_results,
    }
    OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("SUMMARY", json.dumps({k: v for k, v in summary.items() if not k.endswith("_results")}, ensure_ascii=False, indent=2))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
