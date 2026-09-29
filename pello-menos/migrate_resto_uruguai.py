# -*- coding: utf-8 -*-
"""Migra o que falta: Pello Menos - Uruguai (antiga) + residual Franchising -> URG."""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.parse
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
OLD_K = vals["GHL_PELLO_URUGUAI_OLD_API_KEY"]
OLD_L = vals["GHL_PELLO_URUGUAI_OLD_LOCATION_ID"]
URG_K = vals["GHL_PELLO_URG_API_KEY"]
URG_L = vals["GHL_PELLO_URG_LOCATION_ID"]
ASSIGN = "ErRC1xVcZ8zY3XYj6agY"
URG_OWNERS = {"0oiDGUCBjbRFs7xstVhX", "rcbSJ53mHKQE6Jl8nMv3"}


def req(token, method, url, body=None):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode()
    headers = {
        "Authorization": "Bearer " + token,
        "Version": "2021-07-28",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    r = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(r, timeout=90) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"raw": raw[:400]}


def norm(s):
    s = (s or "").lower()
    s = re.sub(r"[^\w\s\[\]|]", "", s, flags=re.UNICODE)
    return re.sub(r"\s+", " ", s).strip()


def fetch_contacts(token, loc):
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
        out.extend(batch)
        total = d.get("total") or 0
        if not batch or len(out) >= total:
            break
        page += 1
        if page > 80:
            break
    return out


def fetch_opps(token, loc, query=None):
    out = []
    seen = set()
    page = 1
    while True:
        url = f"https://services.leadconnectorhq.com/opportunities/search?location_id={loc}&limit=100&page={page}"
        if query:
            url += "&q=" + urllib.parse.quote(query)
        st, d = req(token, "GET", url)
        if query and page == 1 and (st != 200 or not (d.get("opportunities") if isinstance(d, dict) else None)):
            st, d = req(
                token,
                "POST",
                "https://services.leadconnectorhq.com/opportunities/search",
                {"locationId": loc, "query": query, "limit": 100},
            )
        batch = d.get("opportunities") if isinstance(d, dict) else []
        for o in batch or []:
            if o.get("id") not in seen:
                seen.add(o.get("id"))
                out.append(o)
        meta = d.get("meta") if isinstance(d, dict) else {}
        total = (meta or {}).get("total")
        print("  opps page", page, "st", st, "batch", len(batch or []), "seen", len(out), "total", total, "q", query)
        if not batch or len(batch) < 100:
            break
        if total and len(out) >= int(total):
            break
        page += 1
        if page > 40:
            break
    return out


def index(contacts):
    by_p, by_e = {}, {}
    for c in contacts:
        ph = (c.get("phone") or "").strip()
        em = (c.get("email") or "").strip().lower()
        if ph:
            by_p[ph] = c.get("id")
        if em:
            by_e[em] = c.get("id")
    return by_p, by_e


def pipes(token, loc):
    st, d = req(token, "GET", "https://services.leadconnectorhq.com/opportunities/pipelines?locationId=" + loc)
    return d.get("pipelines") or []


def maps(old_pipes, new_pipes):
    new_by = {norm(p.get("name")): p for p in new_pipes}
    pipe_map, stage_map = {}, {}
    fb_pipe = fb_stage = None
    for p in new_pipes:
        if "vendas" in (p.get("name") or "").lower():
            fb_pipe = p["id"]
            stgs = p.get("stages") or []
            fb_stage = stgs[0]["id"] if stgs else None
            break
    if not fb_pipe and new_pipes:
        fb_pipe = new_pipes[0]["id"]
        stgs = new_pipes[0].get("stages") or []
        fb_stage = stgs[0]["id"] if stgs else None
    for op in old_pipes:
        np = None
        for p in new_pipes:
            if "vendas" in (p.get("name") or "").lower() and "vendas" in (op.get("name") or "").lower():
                np = p
                break
        if not np:
            continue
        pipe_map[op["id"]] = np["id"]
        ns = {}
        for s in np.get("stages") or []:
            ns[norm(s.get("name"))] = s["id"]
            ns[norm((s.get("name") or "").split("|")[-1])] = s["id"]
        for s in op.get("stages") or []:
            nid = ns.get(norm(s.get("name"))) or ns.get(norm((s.get("name") or "").split("|")[-1]))
            if nid:
                stage_map[s["id"]] = nid
    return pipe_map, stage_map, fb_pipe, fb_stage


def create_contact(src, tag):
    tags = list(src.get("tags") or [])
    if tag not in tags:
        tags.append(tag)
    body = {
        "locationId": URG_L,
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
        "companyName": src.get("companyName") or None,
        "source": src.get("source") or tag,
        "assignedTo": ASSIGN,
        "tags": tags,
    }
    body = {k: v for k, v in body.items() if v not in (None, "")}
    body["locationId"] = URG_L
    body["tags"] = tags
    body["assignedTo"] = ASSIGN
    st, d = req(URG_K, "POST", "https://services.leadconnectorhq.com/contacts/", body)
    if st in (200, 201):
        return True, (d.get("contact") or d).get("id"), None
    return False, None, f"{st} {json.dumps(d, ensure_ascii=False)[:350]}"


def create_opp(src, ncid, pipe_map, stage_map, fb_pipe, fb_stage):
    new_pipe = pipe_map.get(src.get("pipelineId")) or fb_pipe
    new_stage = stage_map.get(src.get("pipelineStageId")) or fb_stage
    if not new_pipe or not new_stage:
        return False, None, "sem pipeline destino"
    status = src.get("status") or "open"
    if status not in ("open", "won", "lost", "abandoned"):
        status = "open"
    body = {
        "locationId": URG_L,
        "pipelineId": new_pipe,
        "pipelineStageId": new_stage,
        "contactId": ncid,
        "name": src.get("name") or "Oportunidade",
        "status": status,
        "monetaryValue": src.get("monetaryValue") or 0,
        "source": src.get("source") or "uruguai-migrate",
        "assignedTo": ASSIGN,
    }
    st, d = req(URG_K, "POST", "https://services.leadconnectorhq.com/opportunities/", body)
    if st in (200, 201):
        return True, (d.get("opportunity") or d).get("id"), None
    return False, None, f"{st} {json.dumps(d, ensure_ascii=False)[:350]}"


def run_batch(label, contacts, opps, dest, pipe_map, stage_map, fb_pipe, fb_stage, tag):
    by_p, by_e = index(dest)
    id_map = {}
    cres, ores = [], []
    print(f"\n--- {label} contacts {len(contacts)} opps {len(opps)} ---")
    for i, c in enumerate(contacts, 1):
        oid = c.get("id")
        ph = (c.get("phone") or "").strip()
        em = (c.get("email") or "").strip().lower()
        if ph and ph in by_p:
            id_map[oid] = by_p[ph]
            cres.append({"old": oid, "new": by_p[ph], "status": "reuse_phone"})
            print(f"[{i}/{len(contacts)}] reuse phone", ph)
            continue
        if em and em in by_e:
            id_map[oid] = by_e[em]
            cres.append({"old": oid, "new": by_e[em], "status": "reuse_email"})
            print(f"[{i}/{len(contacts)}] reuse email", em)
            continue
        ok, nid, err = create_contact(c, tag)
        if ok:
            id_map[oid] = nid
            if ph:
                by_p[ph] = nid
            if em:
                by_e[em] = nid
            dest.append({"id": nid, "phone": ph, "email": em})
            cres.append({"old": oid, "new": nid, "status": "created"})
            print(f"[{i}/{len(contacts)}] created", c.get("contactName") or c.get("firstName"), nid)
        else:
            cres.append({"old": oid, "status": "error", "error": err})
            print(f"[{i}/{len(contacts)}] ERR", err)
        time.sleep(0.12)
    for i, o in enumerate(opps, 1):
        ocid = o.get("contactId") or ((o.get("contact") or {}).get("id"))
        ncid = id_map.get(ocid)
        if not ncid:
            ores.append({"old": o.get("id"), "status": "skip_no_contact", "name": o.get("name")})
            print(f"[opp {i}/{len(opps)}] skip", o.get("name"))
            continue
        ok, nid, err = create_opp(o, ncid, pipe_map, stage_map, fb_pipe, fb_stage)
        if ok:
            ores.append({"old": o.get("id"), "new": nid, "status": "created"})
            print(f"[opp {i}/{len(opps)}] created", o.get("name"))
        else:
            status = "dup" if "duplicate" in (err or "").lower() else "error"
            ores.append({"old": o.get("id"), "status": status, "error": err})
            print(f"[opp {i}/{len(opps)}] {status}", o.get("name"), err[:80] if err else "")
        time.sleep(0.12)
    return {
        "label": label,
        "contacts_created": sum(1 for x in cres if x["status"] == "created"),
        "contacts_reused": sum(1 for x in cres if str(x.get("status", "")).startswith("reuse")),
        "contacts_error": sum(1 for x in cres if x["status"] == "error"),
        "opps_created": sum(1 for x in ores if x["status"] == "created"),
        "opps_dup": sum(1 for x in ores if x["status"] == "dup"),
        "opps_skip": sum(1 for x in ores if str(x.get("status", "")).startswith("skip")),
        "opps_error": sum(1 for x in ores if x["status"] == "error"),
        "contact_results": cres,
        "opp_results": ores,
    }


def main():
    dest = fetch_contacts(URG_K, URG_L)
    print("dest URG contacts", len(dest))
    old_c = fetch_contacts(OLD_K, OLD_L)
    old_o = fetch_opps(OLD_K, OLD_L)
    print("antiga contacts", len(old_c), "opps", len(old_o))

    fran_c = fetch_contacts(FK, FLOC)
    extra = []
    for c in fran_c:
        owner = c.get("assignedTo") or ""
        blob = " ".join(
            [c.get("contactName") or "", c.get("name") or "", c.get("source") or "", " ".join(c.get("tags") or [])]
        ).lower()
        if owner in URG_OWNERS:
            continue  # já migrados no passo anterior
        if owner == "xHPu5HbnVNPF6QuPnf73" and "gurgel" in blob:
            continue  # falso positivo SJC
        if any(x in blob for x in ("uruguai",)) or (not owner and ("urg" in blob or "amada por deus" in blob)):
            extra.append(c)
    fran_o = []
    st, d = req(
        FK,
        "POST",
        "https://services.leadconnectorhq.com/opportunities/search",
        {"locationId": FLOC, "query": "Uruguai", "limit": 100},
    )
    fran_o.extend(d.get("opportunities") or [])
    print("franchising extras contacts", len(extra), "opps query Uruguai", len(fran_o))
    for c in extra:
        print(" extra", c.get("id"), c.get("contactName") or c.get("name"), c.get("phone"), c.get("assignedTo"))

    old_pipes = pipes(OLD_K, OLD_L)
    fran_pipes = pipes(FK, FLOC)
    dest_pipes = pipes(URG_K, URG_L)
    m1 = maps(old_pipes, dest_pipes)
    m2 = maps(fran_pipes, dest_pipes)

    r1 = run_batch("URUGUAI_ANTIGA", old_c, old_o, dest, *m1, "MIGRADO_URUGUAI_ANTIGA")
    r2 = run_batch("FRANCHISING_EXTRA", extra, [], dest, *m2, "MIGRADO_FRANCHISING")

    dest2 = fetch_contacts(URG_K, URG_L)
    dest_o = fetch_opps(URG_K, URG_L)
    summary = {
        "antiga": {k: v for k, v in r1.items() if not k.endswith("_results")},
        "franchising_extra": {k: v for k, v in r2.items() if not k.endswith("_results")},
        "urg_dest_contacts": len(dest2),
        "urg_dest_opps": len(dest_o),
        "details": {"antiga": r1, "extra": r2},
    }
    (OUT / "migrate-resto-uruguai.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("SUMMARY", json.dumps({k: v for k, v in summary.items() if k != "details"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
