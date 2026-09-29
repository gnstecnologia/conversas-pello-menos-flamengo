# -*- coding: utf-8 -*-
"""Inventário completo: Franchising (tudo Uruguai) + subconta Pello Menos - Uruguai."""
from __future__ import annotations

import json
import sys
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
OLD_K = vals["GHL_PELLO_URUGUAI_OLD_API_KEY"]
OLD_L = vals["GHL_PELLO_URUGUAI_OLD_LOCATION_ID"]
URG_K = vals["GHL_PELLO_URG_API_KEY"]
URG_L = vals["GHL_PELLO_URG_LOCATION_ID"]

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
        with urllib.request.urlopen(r, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"raw": raw[:400]}


def loc(token, locid, label):
    st, d = req(token, "GET", "https://services.leadconnectorhq.com/locations/" + locid)
    L = d.get("location") or d if isinstance(d, dict) else {}
    print(label, st, L.get("name"), L.get("id"))
    return st


def fetch_contacts(token, locid):
    out = []
    page = 1
    while True:
        st, d = req(
            token,
            "POST",
            "https://services.leadconnectorhq.com/contacts/search",
            {"locationId": locid, "page": page, "pageLimit": 100},
        )
        batch = d.get("contacts") or []
        out.extend(batch)
        total = d.get("total") or 0
        print("  contacts", locid[:6], "page", page, len(batch), "seen", len(out), "/", total, "st", st)
        if not batch or len(out) >= total:
            break
        page += 1
        if page > 80:
            break
    return out


def fetch_opps(token, locid, assigned=None):
    out = []
    seen = set()
    start = None
    for i in range(50):
        url = f"https://services.leadconnectorhq.com/opportunities/search?location_id={locid}&limit=100"
        if assigned:
            url += "&assigned_to=" + assigned
        if start:
            url += "&startAfterId=" + start
        st, d = req(token, "GET", url)
        batch = d.get("opportunities") if isinstance(d, dict) else []
        if st != 200:
            print("  opps fail", st, str(d)[:200])
            break
        for o in batch or []:
            if o.get("id") not in seen:
                seen.add(o.get("id"))
                out.append(o)
        print("  opps", locid[:6], "batch", len(batch or []), "seen", len(out), "assigned", assigned)
        if not batch or len(batch) < 100:
            break
        start = batch[-1].get("id")
    return out


def uruguai_hit(text):
    t = (text or "").lower()
    return any(x in t for x in ("uruguai", "urg", "tijuca"))


print("=== LOCS ===")
loc(FK, FLOC, "Franchising")
loc(OLD_K, OLD_L, "Uruguai antiga")
loc(URG_K, URG_L, "URG destino")

print("\n=== URUGUAI ANTIGA ===")
old_c = fetch_contacts(OLD_K, OLD_L)
old_o = fetch_opps(OLD_K, OLD_L)
print("antiga contacts", len(old_c), "opps", len(old_o))

print("\n=== URG DESTINO ===")
urg_c = fetch_contacts(URG_K, URG_L)
urg_o = fetch_opps(URG_K, URG_L)
print("destino contacts", len(urg_c), "opps", len(urg_o))

print("\n=== FRANCHISING ===")
fran_c = fetch_contacts(FK, FLOC)
fran_o = fetch_opps(FK, FLOC)
print("fran contacts", len(fran_c), "opps", len(fran_o))

# Franchising: assigned to URG users OR name/tag/source mentions uruguai
fran_urg_c = []
for c in fran_c:
    blob = " ".join(
        [
            c.get("assignedTo") or "",
            c.get("contactName") or "",
            c.get("name") or "",
            c.get("source") or "",
            " ".join(c.get("tags") or []),
            c.get("companyName") or "",
        ]
    )
    if (c.get("assignedTo") or "") in URG_OWNERS or uruguai_hit(blob):
        fran_urg_c.append(c)

fran_urg_o = []
for o in fran_o:
    cid = o.get("contactId") or ((o.get("contact") or {}).get("id"))
    blob = " ".join(
        [
            o.get("assignedTo") or "",
            o.get("name") or "",
            o.get("source") or "",
            ((o.get("contact") or {}).get("name") or ""),
        ]
    )
    if (o.get("assignedTo") or "") in URG_OWNERS or uruguai_hit(blob):
        fran_urg_o.append(o)

print("\n=== FRANCHISING FILTRO URUGUAI ===")
print("contatos", len(fran_urg_c))
by_owner = {}
for c in fran_urg_c:
    by_owner[c.get("assignedTo") or "(sem)"] = by_owner.get(c.get("assignedTo") or "(sem)", 0) + 1
print(" por assignedTo", by_owner)
print("opps", len(fran_urg_o))

payload = {
    "old_uruguai": {
        "location": OLD_L,
        "contacts": len(old_c),
        "opps": len(old_o),
        "contact_ids": [c.get("id") for c in old_c],
        "opp_ids": [o.get("id") for o in old_o],
    },
    "franchising_uruguai": {
        "contacts": len(fran_urg_c),
        "opps": len(fran_urg_o),
        "contact_ids": [c.get("id") for c in fran_urg_c],
        "opp_ids": [o.get("id") for o in fran_urg_o],
        "contacts_brief": [
            {
                "id": c.get("id"),
                "name": c.get("contactName") or c.get("name"),
                "phone": c.get("phone"),
                "email": c.get("email"),
                "assignedTo": c.get("assignedTo"),
            }
            for c in fran_urg_c
        ],
    },
    "urg_dest": {"contacts": len(urg_c), "opps": len(urg_o)},
}
(OUT / "inventario-tudo-uruguai.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print("saved")
