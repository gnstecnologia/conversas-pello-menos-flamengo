# -*- coding: utf-8 -*-
"""Restringe usuários das lojas Pello a UMA location (a da própria subconta)."""
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
vals = {}
for line in Path(r"c:\Users\GC1\Desktop\Automação GHL\.env").read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()

AG = vals["GHL_AGENCY_API_KEY"]
COMPANY = vals["GHL_AGENCY_COMPANY_ID"]
BASE = "https://services.leadconnectorhq.com"
TEMPLATE = json.loads(
    Path(r"c:\Users\GC1\Desktop\Automação GHL\pello-menos\snp-user-template.json").read_text(encoding="utf-8")
)

# usuarios multi-conta -> so a location da loja
FIXES = [
    ("FLA", "y3WSdOwVSPCzyw59wk1Y", "fla@pellomenos.com.br", "NVole6OHB4Zwe7WtjXAA"),
    ("HUT", "Fpp5MAwAFHSocu8Cz5yw", "huttreinamento2026@gmail.com", "pGPtNsSrtbz5DH9x3kXC"),
    ("IGO2", "q2d7GuBxMgbnh8cY1uYP", "igo2@pellomenos.com.br", "ebNTKkGbZDJogBLTUVvP"),
    ("LBI", "tSWmqvvJyxQfDPcgeIon", "lbi@pellomenos.com.br", "iWMsfmAtJU97tEvl6TbI"),
    ("LBI-teste", "ZmJsuCKTHMhUN3foBSR1", "teste@companygenesis.com.br", "iWMsfmAtJU97tEvl6TbI"),
    ("SP-SJC", "xHPu5HbnVNPF6QuPnf73", "sp-sjc@pellomenos.com.br", "Bv1uUawu8EjmjcWYXbON"),
]


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
            return e.code, {"raw": raw[:400]}


for label, uid, email, only_loc in FIXES:
    st, cur = req(AG, "GET", BASE + "/users/" + uid)
    u = cur.get("user") or cur
    roles = u.get("roles") or {}
    before = roles.get("locationIds") or []
    print(f"=== {label} {email} ===")
    print("antes", before)
    if before == [only_loc]:
        print("ja ok")
        continue
    perms = u.get("permissions") or TEMPLATE["permissions"]
    # se permissions vazias/None keys, usa template
    if not perms or perms.get("assignedDataOnly") is None:
        perms = TEMPLATE["permissions"]
    body = {
        "companyId": COMPANY,
        "firstName": u.get("firstName") or "Unidade",
        "lastName": u.get("lastName") or label,
        "email": email,
        "type": "account",
        "role": "user",
        "locationIds": [only_loc],
        "permissions": perms,
        "scopes": u.get("scopes") or TEMPLATE.get("scopes"),
        "scopesAssignedToOnly": u.get("scopesAssignedToOnly") or TEMPLATE.get("scopesAssignedToOnly"),
    }
    st, out = req(AG, "PUT", BASE + "/users/" + uid, body)
    after = ((out.get("user") or out).get("roles") or {}).get("locationIds") if isinstance(out, dict) else None
    print("PUT", st, "depois", after)
    # confirm GET
    st, cur = req(AG, "GET", BASE + "/users/" + uid)
    u2 = cur.get("user") or cur
    print("confirm", (u2.get("roles") or {}).get("locationIds"))
