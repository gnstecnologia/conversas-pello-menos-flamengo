# -*- coding: utf-8 -*-
"""Copia contatos + oportunidades Franchising -> URG (e LBI se a subconta estiver ativa)."""
from __future__ import annotations

import json
import re
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
URG_K = vals["GHL_PELLO_URG_API_KEY"]
URG_L = vals["GHL_PELLO_URG_LOCATION_ID"]
LBI_K = vals["GHL_PELLO_MODELO_API_KEY"]
LBI_L = vals["GHL_PELLO_MODELO_LOCATION_ID"]

OWNERS = {
    "URG": ["0oiDGUCBjbRFs7xstVhX", "rcbSJ53mHKQE6Jl8nMv3"],
    "LBI": ["tSWmqvvJyxQfDPcgeIon", "R7zlp4VyVaqQFzhd7CGW"],
}
DEST_ASSIGN = {
    "URG": "ErRC1xVcZ8zY3XYj6agY",  # snp@ na URG
    "LBI": "tSWmqvvJyxQfDPcgeIon",  # lbi@ (se existir na LBI)
}


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
            return e.code, {"raw": raw[:400]}


def norm(s):
    s = (s or "").lower()
    s = re.sub(r"[^\w\s\[\]|]", "", s, flags=re.UNICODE)
    return re.sub(r"\s+", " ", s).strip()


def fetch_contacts_by_owner(token, loc, owner_ids):
    wanted = set(owner_ids)
    out = []
    page = 1
    while True:
        st, d = req(
            token,
            "POST",
            "https://services.leadconnectorhq.com/contacts/search",
            {"locationId": loc, "page": page, "pageLimit": 100},
        )
        batch = d.get("contacts") or []
        for c in batch:
            if (c.get("assignedTo") or "") in wanted:
                out.append(c)
        total = d.get("total") or 0
        if not batch or page * 100 >= total:
            break
        page += 1
        if page > 80:
            break
    return out


def fetch_opps_assigned(token, loc, owner_ids):
    opps = []
    seen = set()
    for uid in owner_ids:
        start = None
        for _ in range(40):
            url = (
                "https://services.leadconnectorhq.com/opportunities/search"
                f"?location_id={loc}&assigned_to={uid}&limit=100"
            )
            if start:
                url += "&startAfterId=" + start
            st, d = req(token, "GET", url)
            batch = d.get("opportunities") or []
            if st != 200:
                print("  opp fetch", uid, st, str(d)[:180])
                break
            for o in batch:
                oid = o.get("id")
                if oid and oid not in seen:
                    seen.add(oid)
                    opps.append(o)
            if len(batch) < 100:
                break
            start = batch[-1].get("id")
    return opps


def fetch_all_dest_contacts(token, loc):
    contacts = []
    page = 1
    while True:
        st, d = req(
            token,
            "POST",
            "https://services.leadconnectorhq.com/contacts/search",
            {"locationId": loc, "page": page, "pageLimit": 100},
        )
        if st != 200:
            return contacts, st, d
        batch = d.get("contacts") or []
        contacts.extend(batch)
        total = d.get("total") or 0
        if not batch or len(contacts) >= total:
            break
        page += 1
        if page > 80:
            break
    return contacts, 200, None


def index_contacts(contacts):
    by_phone, by_email = {}, {}
    for c in contacts:
        ph = (c.get("phone") or "").strip()
        em = (c.get("email") or "").strip().lower()
        if ph:
            by_phone[ph] = c.get("id")
        if em:
            by_email[em] = c.get("id")
    return by_phone, by_email


def get_pipelines(token, loc):
    st, d = req(token, "GET", "https://services.leadconnectorhq.com/opportunities/pipelines?locationId=" + loc)
    return d.get("pipelines") or []


def build_maps(old_pipes, new_pipes):
    new_by = {norm(p.get("name")): p for p in new_pipes}
    # also last token after |
    for p in new_pipes:
        parts = (p.get("name") or "").split("|")
        new_by.setdefault(norm(parts[-1]), p)
    pipe_map, stage_map = {}, {}
    fallback_pipe = new_pipes[0]["id"] if new_pipes else None
    fallback_stage = None
    if new_pipes:
        stages = new_pipes[0].get("stages") or []
        fallback_stage = stages[0]["id"] if stages else None
        # prefer Painel Franqueado if exists
        for p in new_pipes:
            if "franqueado" in (p.get("name") or "").lower() or "vendas" in (p.get("name") or "").lower():
                if "vendas" in (p.get("name") or "").lower():
                    fallback_pipe = p["id"]
                    stgs = p.get("stages") or []
                    fallback_stage = stgs[0]["id"] if stgs else fallback_stage
                    break
    for op in old_pipes:
        np = new_by.get(norm(op.get("name")))
        if not np:
            # Pipeline de Vendas match
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
    return pipe_map, stage_map, fallback_pipe, fallback_stage


def create_contact(token, loc, src, assigned):
    tags = list(src.get("tags") or [])
    if "MIGRADO_FRANCHISING" not in tags:
        tags.append("MIGRADO_FRANCHISING")
    body = {
        "locationId": loc,
        "firstName": src.get("firstName") or "",
        "lastName": src.get("lastName") or "",
        "name": src.get("contactName") or src.get("name") or "",
        "email": src.get("email") or None,
        "phone": src.get("phone") or None,
        "address1": src.get("address") or src.get("address1") or None,
        "city": src.get("city") or None,
        "state": src.get("state") or None,
        "postalCode": src.get("postalCode") or None,
        "country": src.get("country") or None,
        "website": src.get("website") or None,
        "companyName": src.get("companyName") or src.get("businessName") or None,
        "source": src.get("source") or "franchising-migrate",
        "tags": tags,
    }
    if assigned:
        body["assignedTo"] = assigned
    body = {k: v for k, v in body.items() if v not in (None, "")}
    body["locationId"] = loc
    if tags:
        body["tags"] = tags
    st, d = req(token, "POST", "https://services.leadconnectorhq.com/contacts/", body)
    if st in (200, 201):
        c = d.get("contact") or d
        return True, c.get("id"), None
    msg = json.dumps(d, ensure_ascii=False) if not isinstance(d, str) else d
    return False, None, f"{st} {msg[:400]}"


def create_opportunity(token, loc, src, new_contact_id, pipe_map, stage_map, fb_pipe, fb_stage, assigned):
    new_pipe = pipe_map.get(src.get("pipelineId")) or fb_pipe
    new_stage = stage_map.get(src.get("pipelineStageId")) or fb_stage
    if not new_pipe or not new_stage:
        return False, None, "sem pipeline/stage destino"
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
        "source": src.get("source") or "franchising-migrate",
    }
    if assigned:
        body["assignedTo"] = assigned
    st, d = req(token, "POST", "https://services.leadconnectorhq.com/opportunities/", body)
    if st in (200, 201):
        o = d.get("opportunity") or d
        return True, o.get("id"), None
    msg = json.dumps(d, ensure_ascii=False) if not isinstance(d, str) else d
    return False, None, f"{st} {msg[:400]}"


def migrate(label, dest_token, dest_loc, owner_ids, assigned):
    print("\n========", label, "========")
    st, locd = req(dest_token, "GET", "https://services.leadconnectorhq.com/locations/" + dest_loc)
    name = (locd.get("location") or locd).get("name") if isinstance(locd, dict) else None
    print("dest", st, name, dest_loc)
    if st != 200:
        print("BLOQUEADO — subconta destino inacessível. Não migrei", label)
        return {"label": label, "blocked": True, "error": locd}

    src_contacts = fetch_contacts_by_owner(FK, FLOC, owner_ids)
    src_opps = fetch_opps_assigned(FK, FLOC, owner_ids)
    print("source contacts", len(src_contacts), "opps", len(src_opps))

    dest_contacts, stc, err = fetch_all_dest_contacts(dest_token, dest_loc)
    if stc != 200:
        print("dest contacts fail", stc, err)
        return {"label": label, "blocked": True, "error": err}
    by_phone, by_email = index_contacts(dest_contacts)
    print("dest already", len(dest_contacts))

    old_pipes = get_pipelines(FK, FLOC)
    new_pipes = get_pipelines(dest_token, dest_loc)
    pipe_map, stage_map, fb_pipe, fb_stage = build_maps(old_pipes, new_pipes)
    print("pipe map", len(pipe_map), "stage map", len(stage_map), "fallback", fb_pipe)

    id_map = {}
    contact_results = []
    for i, c in enumerate(src_contacts, 1):
        oid = c.get("id")
        ph = (c.get("phone") or "").strip()
        em = (c.get("email") or "").strip().lower()
        if ph and ph in by_phone:
            id_map[oid] = by_phone[ph]
            contact_results.append({"old": oid, "new": by_phone[ph], "status": "reuse_phone"})
            print(f"[{i}/{len(src_contacts)}] reuse phone", ph)
            continue
        if em and em in by_email:
            id_map[oid] = by_email[em]
            contact_results.append({"old": oid, "new": by_email[em], "status": "reuse_email"})
            print(f"[{i}/{len(src_contacts)}] reuse email", em)
            continue
        ok, nid, err = create_contact(dest_token, dest_loc, c, assigned)
        if ok:
            id_map[oid] = nid
            if ph:
                by_phone[ph] = nid
            if em:
                by_email[em] = nid
            contact_results.append({"old": oid, "new": nid, "status": "created"})
            print(f"[{i}/{len(src_contacts)}] created", c.get("contactName") or c.get("firstName"), nid)
        else:
            contact_results.append({"old": oid, "status": "error", "error": err})
            print(f"[{i}/{len(src_contacts)}] ERR", err)
        time.sleep(0.12)

    opp_results = []
    for i, o in enumerate(src_opps, 1):
        ocid = o.get("contactId") or ((o.get("contact") or {}).get("id"))
        ncid = id_map.get(ocid)
        if not ncid:
            # try find dest by later creating? skip
            opp_results.append({"old": o.get("id"), "status": "skip_no_contact", "oldContact": ocid})
            print(f"[opp {i}/{len(src_opps)}] skip no contact", o.get("name"))
            continue
        ok, nid, err = create_opportunity(
            dest_token, dest_loc, o, ncid, pipe_map, stage_map, fb_pipe, fb_stage, assigned
        )
        if ok:
            opp_results.append({"old": o.get("id"), "new": nid, "status": "created"})
            print(f"[opp {i}/{len(src_opps)}] created", o.get("name"), nid)
        else:
            opp_results.append({"old": o.get("id"), "status": "error", "error": err})
            print(f"[opp {i}/{len(src_opps)}] ERR", err)
        time.sleep(0.12)

    summary = {
        "label": label,
        "blocked": False,
        "source_contacts": len(src_contacts),
        "source_opps": len(src_opps),
        "contacts_created": sum(1 for x in contact_results if x["status"] == "created"),
        "contacts_reused": sum(1 for x in contact_results if str(x.get("status", "")).startswith("reuse")),
        "contacts_error": sum(1 for x in contact_results if x["status"] == "error"),
        "opps_created": sum(1 for x in opp_results if x["status"] == "created"),
        "opps_error": sum(1 for x in opp_results if x["status"] == "error"),
        "opps_skip": sum(1 for x in opp_results if str(x.get("status", "")).startswith("skip")),
        "contact_results": contact_results,
        "opp_results": opp_results,
    }
    (OUT / f"migrate-{label.lower()}-result.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("SUMMARY", {k: v for k, v in summary.items() if not k.endswith("_results")})
    return summary


def main():
    only = (sys.argv[1] if len(sys.argv) > 1 else "ALL").upper()
    results = []
    if only in ("URG", "ALL"):
        results.append(migrate("URG", URG_K, URG_L, OWNERS["URG"], DEST_ASSIGN["URG"]))
    if only in ("LBI", "ALL"):
        results.append(migrate("LBI", LBI_K, LBI_L, OWNERS["LBI"], DEST_ASSIGN["LBI"]))
    (OUT / "migrate-franchising-urg-lbi-summary.json").write_text(
        json.dumps(
            [{k: v for k, v in r.items() if not k.endswith("_results")} for r in results],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
