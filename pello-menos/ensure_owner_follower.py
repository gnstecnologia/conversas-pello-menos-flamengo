# -*- coding: utf-8 -*-
"""Dono e seguidor = usuário da subconta, em todos os contatos e leads."""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ENV = Path(r"c:\Users\GC1\Desktop\Automação GHL\.env")
vals = {}
for line in ENV.read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()

BASE = "https://services.leadconnectorhq.com"
ACCOUNTS = {
    "COPA2": (
        vals["GHL_PELLO_COPA2_API_KEY"],
        vals["GHL_PELLO_COPA2_LOCATION_ID"],
        "acpaula1970@gmail.com",
    ),
    "FLA": (
        vals["GHL_PELLO_FLA_API_KEY"],
        vals["GHL_PELLO_FLA_LOCATION_ID"],
        "fla@pellomenos.com.br",
    ),
    "SPSJC": (
        vals["GHL_PELLO_SPSJC_API_KEY"],
        vals["GHL_PELLO_SPSJC_LOCATION_ID"],
        "sp-sjc@pellomenos.com.br",
    ),
    "IGO2": (
        vals["GHL_PELLO_IGO2_API_KEY"],
        vals["GHL_PELLO_IGO2_LOCATION_ID"],
        "igo2@pellomenos.com.br",
    ),
    "BOT": (
        vals["GHL_PELLO_BOT_API_KEY"],
        vals["GHL_PELLO_BOT_LOCATION_ID"],
        ["treinamentobot2025@gmail.com", "bottreinamento2025@gmail.com"],
    ),
    "HUT": (
        vals["GHL_PELLO_HUT_API_KEY"],
        vals["GHL_PELLO_HUT_LOCATION_ID"],
        "huttreinamento2026@gmail.com",
    ),
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
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"raw": raw[:300]}


def all_contacts(token, loc):
    out = []
    page = 1
    while True:
        st, d = req(token, "POST", BASE + "/contacts/search", {"locationId": loc, "page": page, "pageLimit": 100})
        if st != 200:
            print("contacts search", st, str(d)[:200])
            break
        batch = d.get("contacts") or []
        out.extend(batch)
        total = d.get("total") or 0
        if not batch or len(out) >= total:
            break
        page += 1
    return out


def all_opps(token, loc):
    out = []
    seen = set()
    start_after = None
    start_id = None
    for _ in range(40):
        url = f"{BASE}/opportunities/search?location_id={loc}&limit=100"
        if start_after and start_id:
            url += f"&startAfter={start_after}&startAfterId={start_id}"
        st, d = req(token, "GET", url)
        if st != 200:
            print("opps", st, str(d)[:200])
            break
        batch = d.get("opportunities") or []
        for o in batch:
            if o.get("id") and o["id"] not in seen:
                seen.add(o["id"])
                out.append(o)
        meta = d.get("meta") or {}
        if len(batch) < 100 or not meta.get("nextPage"):
            break
        start_after = meta.get("startAfter")
        start_id = meta.get("startAfterId")
    return out


def user_id(token, loc, email):
    emails = email if isinstance(email, (list, tuple)) else [email]
    emails = [e.lower() for e in emails]
    st, d = req(token, "GET", BASE + "/users/?locationId=" + loc)
    for u in (d.get("users") or []) if isinstance(d, dict) else []:
        if (u.get("email") or "").lower() in emails:
            return u.get("id")
    print("user nao encontrado", emails, st)
    return None


def add_follower(token, cid, uid):
    return req(token, "POST", BASE + f"/contacts/{cid}/followers", {"followers": [uid]})


def run(label):
    token, loc, email = ACCOUNTS[label]
    uid = user_id(token, loc, email)
    print("===", label, email, uid)
    if not uid:
        return
    contacts = all_contacts(token, loc)
    opps = all_opps(token, loc)
    print(label, "contatos", len(contacts), "leads", len(opps))
    c_ok = f_ok = o_ok = 0
    f_sample = None
    for i, c in enumerate(contacts, 1):
        cid = c.get("id")
        if c.get("assignedTo") != uid:
            st, _ = req(token, "PUT", BASE + "/contacts/" + cid, {"assignedTo": uid})
            if st in (200, 201):
                c_ok += 1
        else:
            c_ok += 1
        st, body = add_follower(token, cid, uid)
        if f_sample is None:
            f_sample = (st, str(body)[:160])
            print("follower sample", f_sample)
        if st in (200, 201):
            f_ok += 1
        elif st == 400 and "already the contact owner" in str(body):
            f_ok += 1
        if i % 40 == 0:
            print(label, "contatos", i)
        time.sleep(0.04)
    for i, o in enumerate(opps, 1):
        oid = o.get("id")
        if o.get("assignedTo") != uid:
            st, _ = req(token, "PUT", BASE + "/opportunities/" + oid, {"assignedTo": uid})
            if st in (200, 201):
                o_ok += 1
        else:
            o_ok += 1
        time.sleep(0.04)
    print(label, "owner_contatos", c_ok, "follower", f_ok, "owner_leads", o_ok, "de", len(contacts), len(opps))


if __name__ == "__main__":
    labels = sys.argv[1:] or ["COPA2", "FLA"]
    for label in labels:
        run(label)
