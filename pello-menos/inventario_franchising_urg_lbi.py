# -*- coding: utf-8 -*-
"""Passo 1: inventário URG/LBI na Franchising + status das subcontas destino."""
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
URG_K = vals["GHL_PELLO_URG_API_KEY"]
URG_L = vals["GHL_PELLO_URG_LOCATION_ID"]
LBI_K = vals["GHL_PELLO_MODELO_API_KEY"]
LBI_L = vals["GHL_PELLO_MODELO_LOCATION_ID"]
AGENCY = vals.get("GHL_AGENCY_API_KEY")

OWNERS = {
    "URG": {
        "0oiDGUCBjbRFs7xstVhX": "Unidade Rua Uruguai <urg@pellomenos.com.br>",
        "rcbSJ53mHKQE6Jl8nMv3": "Gerência Uruguai",
    },
    "LBI": {
        "tSWmqvvJyxQfDPcgeIon": "Unidade Largo do Bicão <lbi@pellomenos.com.br>",
        "R7zlp4VyVaqQFzhd7CGW": "Gerência Largo do Bicão",
    },
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
        with urllib.request.urlopen(r, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"raw": raw[:400]}


def loc_status(label, token, loc):
    st, d = req(token, "GET", "https://services.leadconnectorhq.com/locations/" + loc)
    L = d.get("location") or d if isinstance(d, dict) else {}
    print(label, st, L.get("name"), L.get("id"), "deleted", L.get("deleted"), "status", L.get("status"))
    return st, L


def fetch_contacts(token, loc):
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
        print("  contacts page", page, "batch", len(batch), "seen", len(contacts), "/", total)
        if not batch or len(contacts) >= total:
            break
        page += 1
        if page > 80:
            break
    return contacts


def fetch_opps(token, loc):
    opps = []
    page = 1
    while True:
        st, d = req(
            token,
            "POST",
            "https://services.leadconnectorhq.com/opportunities/search",
            {"locationId": loc, "page": page, "pageLimit": 100, "limit": 100},
        )
        batch = d.get("opportunities") or []
        opps.extend(batch)
        total = d.get("meta", {}).get("total") if isinstance(d.get("meta"), dict) else d.get("total")
        print("  opps page", page, "st", st, "batch", len(batch), "seen", len(opps), "total", total)
        if not batch:
            break
        if total and len(opps) >= int(total):
            break
        page += 1
        if page > 80:
            break
    return opps


print("=== DESTINOS ===")
loc_status("Franchising", FK, FLOC)
loc_status("URG dest PIT", URG_K, URG_L)
loc_status("LBI dest PIT", LBI_K, LBI_L)
if AGENCY:
    loc_status("LBI dest AGENCY", AGENCY, LBI_L)
    loc_status("URG dest AGENCY", AGENCY, URG_L)

print("\n=== PIPELINES DESTINO ===")
for label, tok, loc in (("URG", URG_K, URG_L), ("LBI", LBI_K, LBI_L), ("FRAN", FK, FLOC)):
    st, d = req(tok, "GET", "https://services.leadconnectorhq.com/opportunities/pipelines?locationId=" + loc)
    pipes = d.get("pipelines") if isinstance(d, dict) else []
    print(label, "pipes", st, len(pipes) if isinstance(pipes, list) else d)
    if isinstance(pipes, list):
        for p in pipes:
            print("   ", p.get("name"), p.get("id"), "stages", [s.get("name") for s in (p.get("stages") or [])])

print("\n=== FRANCHISING CONTACTS ===")
contacts = fetch_contacts(FK, FLOC)
print("total contacts", len(contacts))

print("\n=== FRANCHISING OPPS ===")
opps = fetch_opps(FK, FLOC)
print("total opps", len(opps))

urg_ids = set(OWNERS["URG"])
lbi_ids = set(OWNERS["LBI"])

urg_c = [c for c in contacts if (c.get("assignedTo") or "") in urg_ids]
lbi_c = [c for c in contacts if (c.get("assignedTo") or "") in lbi_ids]
urg_cids = {c.get("id") for c in urg_c}
lbi_cids = {c.get("id") for c in lbi_c}

urg_o = [
    o
    for o in opps
    if (o.get("assignedTo") or "") in urg_ids or (o.get("contact", {}) or {}).get("id") in urg_cids or o.get("contactId") in urg_cids
]
lbi_o = [
    o
    for o in opps
    if (o.get("assignedTo") or "") in lbi_ids or (o.get("contact", {}) or {}).get("id") in lbi_cids or o.get("contactId") in lbi_cids
]

print("\n=== RESUMO ===")
print("URG contacts", len(urg_c), "opps", len(urg_o))
print("LBI contacts", len(lbi_c), "opps", len(lbi_o))

# dest existing
print("\n=== DESTINO JÁ TEM ===")
for label, tok, loc in (("URG", URG_K, URG_L), ("LBI", LBI_K, LBI_L)):
    try:
        dc = fetch_contacts(tok, loc)
        print(label, "contacts dest", len(dc))
    except Exception as e:
        print(label, "contacts dest FAIL", e)
    try:
        do = fetch_opps(tok, loc)
        print(label, "opps dest", len(do))
    except Exception as e:
        print(label, "opps dest FAIL", e)

payload = {
    "urg_contact_ids": [c.get("id") for c in urg_c],
    "lbi_contact_ids": [c.get("id") for c in lbi_c],
    "urg_opp_ids": [o.get("id") for o in urg_o],
    "lbi_opp_ids": [o.get("id") for o in lbi_o],
    "urg_contacts": [
        {
            "id": c.get("id"),
            "name": c.get("contactName") or c.get("name"),
            "email": c.get("email"),
            "phone": c.get("phone"),
            "assignedTo": c.get("assignedTo"),
        }
        for c in urg_c
    ],
    "lbi_contacts": [
        {
            "id": c.get("id"),
            "name": c.get("contactName") or c.get("name"),
            "email": c.get("email"),
            "phone": c.get("phone"),
            "assignedTo": c.get("assignedTo"),
        }
        for c in lbi_c
    ],
}
(OUT / "inventario-franchising-urg-lbi.json").write_text(
    json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("saved inventario-franchising-urg-lbi.json")
