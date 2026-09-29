# -*- coding: utf-8 -*-
"""Importa os 96 contatos/leads Copa 2 da Franchising para Pello Menos - COPA2 e cria o usuário restrito."""
from __future__ import annotations

import json
import re
import secrets
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ENV = Path(r"c:\Users\GC1\Desktop\Automação GHL\.env")
OUT = Path(r"c:\Users\GC1\Desktop\Automação GHL\pello-menos")
vals = {}
for line in ENV.read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()

FK = vals["GHL_PELLO_API_KEY"]
FLOC = vals["GHL_PELLO_LOCATION_ID"]
DK = vals["GHL_PELLO_COPA2_API_KEY"]
DLOC = vals["GHL_PELLO_COPA2_LOCATION_ID"]
COMPANY = vals["GHL_AGENCY_COMPANY_ID"]
BASE = "https://services.leadconnectorhq.com"
GER = "aT17W0Ji0S4uspb9nvZ7"
UNI = "Z4shUI5dGN5lZGYPKc78"
EMAIL = "acpaula1970@gmail.com"
TEMPLATE = json.loads((OUT / "snp-user-template.json").read_text(encoding="utf-8"))


def req(token, method, url, body=None):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    headers = {
        "Authorization": "Bearer " + token,
        "Version": "2021-07-28",
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
            return e.code, {"raw": raw[:500]}


def norm(s):
    s = (s or "").lower()
    s = re.sub(r"[^\w\s\[\]|]", "", s, flags=re.UNICODE)
    return re.sub(r"\s+", " ", s).strip()


def search_ids(field, value):
    ids = []
    page = 1
    while True:
        st, d = req(
            FK,
            "POST",
            BASE + "/contacts/search",
            {
                "locationId": FLOC,
                "page": page,
                "pageLimit": 100,
                "filters": [{"field": field, "operator": "eq", "value": value}],
            },
        )
        if st != 200:
            raise SystemExit(f"search {field} {st} {d}")
        batch = d.get("contacts") or []
        ids.extend(batch)
        total = d.get("total") or 0
        if not batch or page * 100 >= total:
            break
        page += 1
    return ids


def fetch_opps_for(contact_id):
    st, d = req(
        FK,
        "GET",
        f"{BASE}/opportunities/search?location_id={FLOC}&contact_id={contact_id}&limit=20",
    )
    if st != 200:
        return st, []
    return st, d.get("opportunities") or []


def get_pipelines(token, loc):
    st, d = req(token, "GET", BASE + "/opportunities/pipelines?locationId=" + loc)
    return st, d.get("pipelines") or []


def build_maps(old_pipes, new_pipes):
    new_by = {norm(p.get("name")): p for p in new_pipes}
    for p in new_pipes:
        parts = (p.get("name") or "").split("|")
        new_by.setdefault(norm(parts[-1]), p)
    pipe_map, stage_map = {}, {}
    fb_pipe = new_pipes[0]["id"] if new_pipes else None
    fb_stage = None
    if new_pipes:
        stages = new_pipes[0].get("stages") or []
        fb_stage = stages[0]["id"] if stages else None
        for p in new_pipes:
            if "vendas" in (p.get("name") or "").lower():
                fb_pipe = p["id"]
                stgs = p.get("stages") or []
                fb_stage = stgs[0]["id"] if stgs else fb_stage
                break
    for op in old_pipes:
        np = new_by.get(norm(op.get("name")))
        if not np:
            for p in new_pipes:
                if "vendas" in (p.get("name") or "").lower() and "vendas" in (op.get("name") or "").lower():
                    np = p
                    break
        if not np:
            continue
        pipe_map[op["id"]] = np["id"]
        new_stages = {}
        for s in np.get("stages") or []:
            new_stages[norm(s.get("name"))] = s.get("id")
            parts = (s.get("name") or "").split("|")
            new_stages[norm(parts[-1])] = s.get("id")
        for s in op.get("stages") or []:
            nid = new_stages.get(norm(s.get("name")))
            if not nid:
                parts = (s.get("name") or "").split("|")
                nid = new_stages.get(norm(parts[-1]))
            if nid:
                stage_map[s["id"]] = nid
    return pipe_map, stage_map, fb_pipe, fb_stage


def main():
    st, locd = req(DK, "GET", BASE + "/locations/" + DLOC)
    loc = (locd.get("location") or locd) if isinstance(locd, dict) else {}
    print("dest", st, loc.get("name"), DLOC)
    if st != 200:
        print(locd)
        return

    by_id = {}
    for field, uid in (("assignedTo", UNI), ("assignedTo", GER), ("followers", GER), ("followers", UNI)):
        batch = search_ids(field, uid)
        print("filtro", field, uid[:6], len(batch))
        for c in batch:
            by_id[c["id"]] = c
    contacts = list(by_id.values())
    print("contatos unicos", len(contacts))

    opps = []
    seen_opp = set()
    opp_fail = 0
    for i, c in enumerate(contacts, 1):
        st, batch = fetch_opps_for(c["id"])
        if st != 200:
            opp_fail += 1
        for o in batch:
            if o.get("id") and o["id"] not in seen_opp:
                seen_opp.add(o["id"])
                opps.append(o)
        if i % 20 == 0:
            print("opps scan", i, "found", len(opps))
        time.sleep(0.05)
    print("leads", len(opps), "falhas busca", opp_fail)

    st, dcontacts = req(DK, "POST", BASE + "/contacts/search", {"locationId": DLOC, "page": 1, "pageLimit": 100})
    existing = dcontacts.get("contacts") or [] if st == 200 else []
    total_dest = dcontacts.get("total") or len(existing)
    print("dest ja tinha", total_dest, "status", st)
    by_phone, by_email = {}, {}
    page = 1
    got = []
    while True:
        st, d = req(DK, "POST", BASE + "/contacts/search", {"locationId": DLOC, "page": page, "pageLimit": 100})
        batch = d.get("contacts") or []
        got.extend(batch)
        if not batch or len(got) >= (d.get("total") or 0):
            break
        page += 1
    for c in got:
        if c.get("phone"):
            by_phone[c["phone"].strip()] = c["id"]
        if c.get("email"):
            by_email[c["email"].strip().lower()] = c["id"]

    _, old_pipes = get_pipelines(FK, FLOC)
    stp, new_pipes = get_pipelines(DK, DLOC)
    print("pipes dest", stp, [p.get("name") for p in new_pipes])
    pipe_map, stage_map, fb_pipe, fb_stage = build_maps(old_pipes, new_pipes)

    id_map = {}
    contact_results = []
    for i, c in enumerate(contacts, 1):
        oid = c["id"]
        ph = (c.get("phone") or "").strip()
        em = (c.get("email") or "").strip().lower()
        if ph and ph in by_phone:
            id_map[oid] = by_phone[ph]
            contact_results.append({"old": oid, "new": by_phone[ph], "status": "reuse_phone"})
            print(f"[{i}] reuse phone")
            continue
        if em and em in by_email:
            id_map[oid] = by_email[em]
            contact_results.append({"old": oid, "new": by_email[em], "status": "reuse_email"})
            print(f"[{i}] reuse email")
            continue
        tags = list(c.get("tags") or [])
        for tag in ("MIGRADO_FRANCHISING", "COPA2"):
            if tag not in tags:
                tags.append(tag)
        body = {
            "locationId": DLOC,
            "firstName": c.get("firstName") or "",
            "lastName": c.get("lastName") or "",
            "name": c.get("contactName") or c.get("name") or "",
            "email": c.get("email") or None,
            "phone": c.get("phone") or None,
            "address1": c.get("address") or c.get("address1") or None,
            "city": c.get("city") or None,
            "state": c.get("state") or None,
            "postalCode": c.get("postalCode") or None,
            "country": c.get("country") or None,
            "source": c.get("source") or "franchising-copa2",
            "tags": tags,
        }
        body = {k: v for k, v in body.items() if v not in (None, "")}
        body["locationId"] = DLOC
        body["tags"] = tags
        st, d = req(DK, "POST", BASE + "/contacts/", body)
        if st in (200, 201):
            nid = (d.get("contact") or d).get("id")
            id_map[oid] = nid
            if ph:
                by_phone[ph] = nid
            if em:
                by_email[em] = nid
            contact_results.append({"old": oid, "new": nid, "status": "created", "name": c.get("contactName")})
            print(f"[{i}/{len(contacts)}] created", c.get("contactName") or c.get("firstName"))
        else:
            contact_results.append({"old": oid, "status": "error", "error": str(d)[:300]})
            print(f"[{i}] ERR", str(d)[:180])
        time.sleep(0.1)

    opp_results = []
    for i, o in enumerate(opps, 1):
        ocid = o.get("contactId") or ((o.get("contact") or {}).get("id"))
        ncid = id_map.get(ocid)
        if not ncid:
            opp_results.append({"old": o.get("id"), "status": "skip_no_contact"})
            print(f"[opp {i}] skip")
            continue
        new_pipe = pipe_map.get(o.get("pipelineId")) or fb_pipe
        new_stage = stage_map.get(o.get("pipelineStageId")) or fb_stage
        status = o.get("status") or "open"
        if status not in ("open", "won", "lost", "abandoned"):
            status = "open"
        if not new_pipe or not new_stage:
            opp_results.append({"old": o.get("id"), "status": "error", "error": "sem pipeline"})
            print(f"[opp {i}] sem pipeline")
            continue
        body = {
            "locationId": DLOC,
            "pipelineId": new_pipe,
            "pipelineStageId": new_stage,
            "contactId": ncid,
            "name": o.get("name") or "Oportunidade",
            "status": status,
            "monetaryValue": o.get("monetaryValue") or 0,
            "source": o.get("source") or "franchising-copa2",
        }
        st, d = req(DK, "POST", BASE + "/opportunities/", body)
        if st in (200, 201):
            nid = (d.get("opportunity") or d).get("id")
            opp_results.append({"old": o.get("id"), "new": nid, "status": "created"})
            print(f"[opp {i}/{len(opps)}] created", o.get("name"))
        else:
            opp_results.append({"old": o.get("id"), "status": "error", "error": str(d)[:300]})
            print(f"[opp {i}] ERR", str(d)[:180])
        time.sleep(0.1)

    password = secrets.token_urlsafe(12)
    st, users = req(DK, "GET", BASE + "/users/?locationId=" + DLOC)
    existing_user = None
    for u in (users.get("users") or []) if isinstance(users, dict) else []:
        if (u.get("email") or "").lower() == EMAIL:
            existing_user = u
    perms = TEMPLATE["permissions"]
    if existing_user:
        uid = existing_user["id"]
        print("user ja existe", uid)
    else:
        body = {
            "companyId": COMPANY,
            "firstName": "Paula",
            "lastName": "Copa 2",
            "email": EMAIL,
            "password": password,
            "type": "account",
            "role": "user",
            "locationIds": [DLOC],
            "permissions": perms,
            "scopes": TEMPLATE.get("scopes"),
            "scopesAssignedToOnly": TEMPLATE.get("scopesAssignedToOnly"),
        }
        st, created = req(DK, "POST", BASE + "/users/", body)
        user = (created.get("user") or created) if isinstance(created, dict) else {}
        uid = user.get("id")
        print("POST user", st, uid, user.get("email") or created.get("message") if isinstance(created, dict) else created)
        if st not in (200, 201) or not uid:
            print(str(created)[:500])
            uid = None
        else:
            print("PASSWORD", password)

    assigned_c = assigned_o = 0
    if uid:
        for row in contact_results:
            nid = row.get("new")
            if not nid:
                continue
            st, _ = req(DK, "PUT", BASE + "/contacts/" + nid, {"assignedTo": uid})
            if st in (200, 201):
                assigned_c += 1
            time.sleep(0.05)
        for row in opp_results:
            nid = row.get("new")
            if not nid:
                continue
            st, _ = req(DK, "PUT", BASE + "/opportunities/" + nid, {"assignedTo": uid})
            if st in (200, 201):
                assigned_o += 1
            time.sleep(0.05)
    print("assigned contacts", assigned_c, "opps", assigned_o)

    summary = {
        "contacts_source": len(contacts),
        "opps_source": len(opps),
        "contacts_created": sum(1 for x in contact_results if x["status"] == "created"),
        "contacts_reused": sum(1 for x in contact_results if str(x["status"]).startswith("reuse")),
        "contacts_error": sum(1 for x in contact_results if x["status"] == "error"),
        "opps_created": sum(1 for x in opp_results if x["status"] == "created"),
        "opps_error": sum(1 for x in opp_results if x["status"] == "error"),
        "opps_skip": sum(1 for x in opp_results if str(x["status"]).startswith("skip")),
        "user_id": uid,
        "user_email": EMAIL,
        "assigned_contacts": assigned_c,
        "assigned_opps": assigned_o,
        "contact_results": contact_results,
        "opp_results": opp_results,
    }
    (OUT / "migrate-copa2-result.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("SUMMARY", {k: v for k, v in summary.items() if not k.endswith("_results")})


if __name__ == "__main__":
    main()
