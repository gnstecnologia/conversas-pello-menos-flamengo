# -*- coding: utf-8 -*-
"""Atribui dono (URG=SNP, LBI=lbi@) em contatos e oportunidades e calcula custo WA marketing."""
from __future__ import annotations

import json
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

ACCOUNTS = [
    {
        "label": "URG",
        "key": vals["GHL_PELLO_URG_API_KEY"],
        "loc": vals["GHL_PELLO_URG_LOCATION_ID"],
        "owner": "ErRC1xVcZ8zY3XYj6agY",
        "owner_email": "snp@pellomenos.com.br",
    },
    {
        "label": "LBI",
        "key": vals["GHL_PELLO_MODELO_API_KEY"],
        "loc": vals["GHL_PELLO_MODELO_LOCATION_ID"],
        "owner": "tSWmqvvJyxQfDPcgeIon",
        "owner_email": "lbi@pellomenos.com.br",
    },
]

WA_MKT_BR = 0.0656  # USD por mensagem de marketing entregue (Brasil)


def req(token, method, url, body=None):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode()
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
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"raw": raw[:300]}


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
        print("  contacts page", page, len(batch), "/", total)
        if not batch or len(out) >= total:
            break
        page += 1
        if page > 40:
            break
    return out


def fetch_opps(token, loc):
    out = []
    seen = set()
    page = 1
    while True:
        st, d = req(
            token,
            "GET",
            f"https://services.leadconnectorhq.com/opportunities/search?location_id={loc}&limit=100&page={page}",
        )
        batch = d.get("opportunities") if isinstance(d, dict) else []
        for o in batch or []:
            if o.get("id") not in seen:
                seen.add(o.get("id"))
                out.append(o)
        meta = (d.get("meta") or {}) if isinstance(d, dict) else {}
        print("  opps page", page, "st", st, "batch", len(batch or []), "seen", len(out), "total", meta.get("total"))
        if not batch or len(batch) < 100:
            break
        if meta.get("total") and len(out) >= int(meta["total"]):
            break
        page += 1
        if page > 40:
            break
    return out


def assign_contact(token, cid, owner):
    st, d = req(token, "PUT", "https://services.leadconnectorhq.com/contacts/" + cid, {"assignedTo": owner})
    return st in (200, 201), st, d


def assign_opp(token, oid, owner):
    st, d = req(token, "PUT", "https://services.leadconnectorhq.com/opportunities/" + oid, {"assignedTo": owner})
    return st in (200, 201), st, d


def run_account(acc):
    print("\n========", acc["label"], "->", acc["owner_email"], "========")
    contacts = fetch_contacts(acc["key"], acc["loc"])
    opps = fetch_opps(acc["key"], acc["loc"])
    owner = acc["owner"]
    c_ok = c_skip = c_err = 0
    phones = set()
    for i, c in enumerate(contacts, 1):
        ph = (c.get("phone") or "").strip()
        if ph:
            phones.add(ph)
        if (c.get("assignedTo") or "") == owner:
            c_skip += 1
            continue
        ok, st, d = assign_contact(acc["key"], c["id"], owner)
        if ok:
            c_ok += 1
        else:
            c_err += 1
            print("  contact ERR", c.get("id"), st, str(d)[:160])
        if i % 40 == 0:
            print("  contacts progress", i, "/", len(contacts))
        time.sleep(0.08)

    o_ok = o_skip = o_err = 0
    for i, o in enumerate(opps, 1):
        if (o.get("assignedTo") or "") == owner:
            o_skip += 1
            continue
        ok, st, d = assign_opp(acc["key"], o["id"], owner)
        if ok:
            o_ok += 1
        else:
            o_err += 1
            print("  opp ERR", o.get("id"), st, str(d)[:160])
        if i % 40 == 0:
            print("  opps progress", i, "/", len(opps))
        time.sleep(0.08)

    # verify
    contacts2 = fetch_contacts(acc["key"], acc["loc"])
    opps2 = fetch_opps(acc["key"], acc["loc"])
    c_owned = sum(1 for c in contacts2 if (c.get("assignedTo") or "") == owner)
    o_owned = sum(1 for o in opps2 if (o.get("assignedTo") or "") == owner)
    phones2 = {(c.get("phone") or "").strip() for c in contacts2 if (c.get("phone") or "").strip()}
    n_phone = len(phones2)
    cost = n_phone * WA_MKT_BR
    res = {
        "label": acc["label"],
        "owner": acc["owner_email"],
        "contacts_total": len(contacts2),
        "contacts_assigned_now": c_ok,
        "contacts_already": c_skip,
        "contacts_error": c_err,
        "contacts_owned_verify": c_owned,
        "opps_total": len(opps2),
        "opps_assigned_now": o_ok,
        "opps_already": o_skip,
        "opps_error": o_err,
        "opps_owned_verify": o_owned,
        "phones_unique": n_phone,
        "wa_marketing_usd": round(cost, 2),
        "wa_rate": WA_MKT_BR,
    }
    print("RESULT", res)
    return res


def main():
    results = [run_account(a) for a in ACCOUNTS]
    total_phones = sum(r["phones_unique"] for r in results)
    total_cost = round(total_phones * WA_MKT_BR, 2)
    out = {
        "accounts": results,
        "wa_template_marketing_br_usd_each": WA_MKT_BR,
        "total_phones": total_phones,
        "total_wa_marketing_usd": total_cost,
    }
    (OUT / "assign-owner-wa-cost.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\nTOTAL phones", total_phones, "USD", total_cost)


if __name__ == "__main__":
    main()
