# -*- coding: utf-8 -*-
import json
import sys
import urllib.error
import urllib.parse
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
ACCOUNTS = [
    ("BOT", "kbXjwvXIECaTjRdoE9M8", vals.get("GHL_PELLO_BOT_API_KEY")),
    ("COPA2", "njrlilZK1yNx5RATkDEm", vals.get("GHL_PELLO_COPA2_API_KEY")),
    ("FLA", "NVole6OHB4Zwe7WtjXAA", vals.get("GHL_PELLO_FLA_API_KEY")),
    ("HUT", "pGPtNsSrtbz5DH9x3kXC", vals.get("GHL_PELLO_HUT_API_KEY")),
    ("IGO2", "ebNTKkGbZDJogBLTUVvP", vals.get("GHL_PELLO_IGO2_API_KEY")),
    ("LBI", "iWMsfmAtJU97tEvl6TbI", vals.get("GHL_PELLO_MODELO_API_KEY")),
    ("LMA", "JSsmufl0VhKVinzGUswq", vals.get("GHL_PELLO_LMA_API_KEY")),
    ("PET", "SjgLBZXkWvbCgexOKAw6", vals.get("GHL_PELLO_PET_API_KEY")),
    ("SP-SJC", "Bv1uUawu8EjmjcWYXbON", vals.get("GHL_PELLO_SPSJC_API_KEY")),
    ("URG", "1a0o7zlmuX4HVazkqcFV", vals.get("GHL_PELLO_URG_API_KEY")),
]


def get(token, url):
    r = urllib.request.Request(
        url,
        headers={
            "Authorization": "Bearer " + token,
            "Version": "2021-07-28",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
        },
    )
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"raw": raw[:200]}


for name, loc, pit in ACCOUNTS:
    print(f"=== Pello Menos - {name} ===")
    users = None
    attempts = []
    if pit:
        attempts.append(("pit", pit, BASE + "/users/?locationId=" + loc))
    attempts.append(("agency-list", AG, BASE + "/users/?locationId=" + loc))
    attempts.append(
        (
            "agency-search",
            AG,
            BASE
            + "/users/search?"
            + urllib.parse.urlencode({"companyId": COMPANY, "locationId": loc, "limit": 50}),
        )
    )
    for label, token, url in attempts:
        st, d = get(token, url)
        if st == 200 and isinstance(d, dict):
            users = d.get("users") or []
            print(f"via {label} | {len(users)} usuario(s)")
            break
    if users is None:
        print("sem acesso")
        continue
    if not users:
        print("(nenhum)")
        continue
    for u in sorted(users, key=lambda x: (x.get("email") or "").lower()):
        roles = u.get("roles") or {}
        nm = " ".join(x for x in (u.get("firstName"), u.get("lastName")) if x) or (u.get("name") or "")
        print(f"- {u.get('email')} | {nm.strip()} | role={roles.get('role')} | id={u.get('id')}")
