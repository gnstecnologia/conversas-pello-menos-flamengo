# -*- coding: utf-8 -*-
"""Franchising LBI (unidade + gerência + residual) -> Pello Menos - LBI."""
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
LBI_K = vals["GHL_PELLO_MODELO_API_KEY"]
LBI_L = vals["GHL_PELLO_MODELO_LOCATION_ID"]
OWNERS = ["tSWmqvvJyxQfDPcgeIon", "R7zlp4VyVaqQFzhd7CGW"]
OWNER_SET = set(OWNERS)


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
        if st != 200:
            print("contacts fail", st, d)
            break
        batch = d.get("contacts") or []
        out.extend(batch)
        total = d.get("total") or 0
        print("contacts", loc[:6], "page", page, len(batch), "seen", len(out), "/", total)
        if not batch or len(out) >= total:
            break
        page += 1
        if page > 80:
            break
    return out


def fetch_opps_assigned(token, loc, uids):
    out = []
    seen = set()
    for uid in uids:
        page = 1
        while True:
            url = (
                "https://services.leadconnectorhq.com/opportunities/search"
                f"?location_id={loc}&assigned_to={uid}&limit=100&page={page}"
            )
            st, d = req(token, "GET", url)
            batch = d.get("opportunities") if isinstance(d, dict) else []
            meta = (d.get("meta") or {}) if isinstance(d, dict) else {}
            for o in batch or []:
                if o.get("id") not in seen:
                    seen.add(o.get("id"))
                    out.append(o)
            print("opps", uid[:6], "page", page, "st", st, "batch", len(batch or []), "seen", len(out), "total", meta.get("total"))
            if not batch or len(batch) < 100:
                break
            if meta.get("total") and len([o for o in out if o.get("assignedTo") == uid]) >= int(meta["total"]):
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


def dest_assign():
    st, d = req(LBI_K, "GET", "https://services.leadconnectorhq.com/users/?locationId=" + LBI_L)
    for u in d.get("users") or []:
        em = (u.get("email") or "").lower()
        print("LBI user", u.get("id"), em, u.get("firstName"))
        if em == "lbi@pellomenos.com.br" or u.get("id") == "tSWmqvvJyxQfDPcgeIon":
            return u.get("id")
    return None


def create_contact(src, assigned):
    tags = list(src.get("tags") or [])
    if "MIGRADO_FRANCHISING" not in tags:
        tags.append("MIGRADO_FRANCHISING")
    body = {
        "locationId": LBI_L,
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
        "source": src.get("source") or "franchising-lbi",
        "tags": tags,
    }
    if assigned:
        body["assignedTo"] = assigned
    body = {k: v for k, v in body.items() if v not in (None, "")}
    body["locationId"] = LBI_L
    body["tags"] = tags
    st, d = req(LBI_K, "POST", "https://services.leadconnectorhq.com/contacts/", body)
    if st in (200, 201):
        return True, (d.get("contact") or d).get("id"), None
    return False, None, f"{st} {json.dumps(d, ensure_ascii=False)[:350]}"


def create_opp(src, ncid, pipe_map, stage_map, fb_pipe, fb_stage, assigned):
    new_pipe = pipe_map.get(src.get("pipelineId")) or fb_pipe
    new_stage = stage_map.get(src.get("pipelineStageId")) or fb_stage
    if not new_pipe or not new_stage:
        return False, None, "sem pipeline destino"
    status = src.get("status") or "open"
    if status not in ("open", "won", "lost", "abandoned"):
        status = "open"
    body = {
        "locationId": LBI_L,
        "pipelineId": new_pipe,
        "pipelineStageId": new_stage,
        "contactId": ncid,
        "name": src.get("name") or "Oportunidade",
        "status": status,
        "monetaryValue": src.get("monetaryValue") or 0,
        "source": src.get("source") or "franchising-lbi",
    }
    if assigned:
        body["assignedTo"] = assigned
    st, d = req(LBI_K, "POST", "https://services.leadconnectorhq.com/opportunities/", body)
    if st in (200, 201):
        return True, (d.get("opportunity") or d).get("id"), None
    return False, None, f"{st} {json.dumps(d, ensure_ascii=False)[:350]}"


def main():
    st, locd = req(LBI_K, "GET", "https://services.leadconnectorhq.com/locations/" + LBI_L)
    print("dest", st, (locd.get("location") or locd).get("name") if isinstance(locd, dict) else locd)
    if st != 200:
        print("LBI ainda inativa")
        return

    assigned = dest_assign()
    print("assign dest", assigned)

    fran = fetch_contacts(FK, FLOC)
    src = []
    extras = []
    for c in fran:
        owner = c.get("assignedTo") or ""
        blob = " ".join(
            [c.get("contactName") or "", c.get("name") or "", c.get("source") or "", " ".join(c.get("tags") or [])]
        ).lower()
        if owner in OWNER_SET:
            src.append(c)
        elif any(x in blob for x in ("largo do bic", "bicao", "bicão")):
            extras.append(c)
    print("src assigned", len(src), "extras nome", len(extras))
    for c in extras:
        print(" extra", c.get("id"), c.get("contactName") or c.get("name"), c.get("assignedTo"), c.get("phone"))

    opps = fetch_opps_assigned(FK, FLOC, OWNERS)
    print("src opps", len(opps))

    dest = fetch_contacts(LBI_K, LBI_L)
    by_p, by_e = index(dest)
    print("dest already", len(dest))

    pipe_map, stage_map, fb_pipe, fb_stage = maps(pipes(FK, FLOC), pipes(LBI_K, LBI_L))
    print("pipe map", len(pipe_map), "stages", len(stage_map))

    all_src = src + extras
    id_map = {}
    cres, ores = [], []
    for i, c in enumerate(all_src, 1):
        oid = c.get("id")
        ph = (c.get("phone") or "").strip()
        em = (c.get("email") or "").strip().lower()
        if ph and ph in by_p:
            id_map[oid] = by_p[ph]
            cres.append({"old": oid, "new": by_p[ph], "status": "reuse_phone"})
            print(f"[{i}/{len(all_src)}] reuse phone", ph)
            continue
        if em and em in by_e:
            id_map[oid] = by_e[em]
            cres.append({"old": oid, "new": by_e[em], "status": "reuse_email"})
            print(f"[{i}/{len(all_src)}] reuse email", em)
            continue
        ok, nid, err = create_contact(c, assigned)
        if ok:
            id_map[oid] = nid
            if ph:
                by_p[ph] = nid
            if em:
                by_e[em] = nid
            cres.append({"old": oid, "new": nid, "status": "created"})
            print(f"[{i}/{len(all_src)}] created", c.get("contactName") or c.get("firstName"), nid)
        else:
            cres.append({"old": oid, "status": "error", "error": err})
            print(f"[{i}/{len(all_src)}] ERR", err)
        time.sleep(0.12)

    for i, o in enumerate(opps, 1):
        ocid = o.get("contactId") or ((o.get("contact") or {}).get("id"))
        ncid = id_map.get(ocid)
        if not ncid:
            ores.append({"old": o.get("id"), "status": "skip_no_contact", "name": o.get("name")})
            print(f"[opp {i}/{len(opps)}] skip", o.get("name"))
            continue
        ok, nid, err = create_opp(o, ncid, pipe_map, stage_map, fb_pipe, fb_stage, assigned)
        if ok:
            ores.append({"old": o.get("id"), "new": nid, "status": "created"})
            print(f"[opp {i}/{len(opps)}] created", o.get("name"))
        else:
            status = "dup" if "duplicate" in (err or "").lower() else "error"
            ores.append({"old": o.get("id"), "status": status, "error": err})
            print(f"[opp {i}/{len(opps)}] {status}", o.get("name"), (err or "")[:90])
        time.sleep(0.12)

    dest2 = fetch_contacts(LBI_K, LBI_L)
    st, d = req(LBI_K, "GET", "https://services.leadconnectorhq.com/opportunities/search?location_id=" + LBI_L + "&limit=1")
    dest_opps = (d.get("meta") or {}).get("total") if isinstance(d, dict) else None
    summary = {
        "contacts_created": sum(1 for x in cres if x["status"] == "created"),
        "contacts_reused": sum(1 for x in cres if str(x.get("status", "")).startswith("reuse")),
        "contacts_error": sum(1 for x in cres if x["status"] == "error"),
        "opps_created": sum(1 for x in ores if x["status"] == "created"),
        "opps_dup": sum(1 for x in ores if x["status"] == "dup"),
        "opps_skip": sum(1 for x in ores if str(x.get("status", "")).startswith("skip")),
        "opps_error": sum(1 for x in ores if x["status"] == "error"),
        "dest_contacts": len(dest2),
        "dest_opps": dest_opps,
        "contact_results": cres,
        "opp_results": ores,
    }
    (OUT / "migrate-lbi-result.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("SUMMARY", {k: v for k, v in summary.items() if not k.endswith("_results")})


if __name__ == "__main__":
    main()
