# -*- coding: utf-8 -*-
"""Restaura Filipe e coloca Natasha como admin na Franqueadora via PIT da agência."""
from __future__ import annotations

import json
import sys
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

AGENCY = "pit-704ae0dc-73da-4521-af39-8dad17ebd02d"
FK = vals["GHL_PELLO_API_KEY"]
FLOC = vals["GHL_PELLO_LOCATION_ID"]
KEY = vals["GHL_PELLO_FRANQ_API_KEY"]
LOC = vals["GHL_PELLO_FRANQ_LOCATION_ID"]
COMPANY = "PIK3OmRl8Y7U0cy1tHSR"
FILIPE = "kFKxIEgACVo4xeEwhJ5Y"
NAT = "HpVTiwskOWDTtqTOAAlN"


def req(key, method, url, body=None):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    r = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {key}",
            "Version": "2021-07-28",
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "Mozilla/5.0",
        },
    )
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = raw
        return e.code, parsed


def get_user(key, uid):
    st, data = req(key, "GET", f"https://services.leadconnectorhq.com/users/{uid}")
    u = data.get("user") or data if isinstance(data, dict) else {}
    print("GET", uid, st, u.get("email") if isinstance(u, dict) else data, u.get("roles") if isinstance(u, dict) else "")
    return st, u if isinstance(u, dict) else {}


def listed(key, loc, email_or_id):
    st, data = req(key, "GET", f"https://services.leadconnectorhq.com/users/?locationId={loc}")
    users = (data or {}).get("users") or [] if isinstance(data, dict) else []
    hits = [
        u
        for u in users
        if u.get("id") == email_or_id or (u.get("email") or "").lower() == str(email_or_id).lower()
    ]
    return st, len(users), hits


print("agency locations/search")
st, data = req(AGENCY, "GET", "https://services.leadconnectorhq.com/locations/search?limit=5")
print(" ", st, (data.get("locations") or [{}])[0].get("name") if isinstance(data, dict) else data)

st, filipe = get_user(AGENCY, FILIPE)
stn, natasha = get_user(AGENCY, NAT)
if st != 200:
    st, filipe = get_user(KEY, FILIPE)
if stn != 200:
    stn, natasha = get_user(FK, NAT)

# Restaurar Filipe: Franqueadora + Franchising (como estava nas duas listas)
filipe_locs = list((filipe.get("roles") or {}).get("locationIds") or [])
if FLOC not in filipe_locs:
    filipe_locs.append(FLOC)
if LOC not in filipe_locs:
    filipe_locs.append(LOC)
print("filipe target locs", filipe_locs)
body_f = {
    "companyId": COMPANY,
    "firstName": filipe.get("firstName") or "Filipe",
    "lastName": filipe.get("lastName") or "Lisboa",
    "type": "account",
    "role": "admin",
    "locationIds": filipe_locs,
    "permissions": filipe.get("permissions") or {},
}
st, out = req(AGENCY, "PUT", f"https://services.leadconnectorhq.com/users/{FILIPE}", body_f)
print("PUT filipe agency", st, (out.get("roles") if isinstance(out, dict) else out), (out.get("message") if isinstance(out, dict) else None))

# Natasha: locais atuais + Franqueadora
nat_locs = list((natasha.get("roles") or {}).get("locationIds") or [])
if LOC not in nat_locs:
    nat_locs.append(LOC)
print("natasha target locs", nat_locs)
body_n = {
    "companyId": COMPANY,
    "firstName": natasha.get("firstName") or "Natasha",
    "lastName": natasha.get("lastName") or "Souza",
    "type": "account",
    "role": "admin",
    "locationIds": nat_locs,
    "permissions": natasha.get("permissions") or {},
}
st, out = req(AGENCY, "PUT", f"https://services.leadconnectorhq.com/users/{NAT}", body_n)
print("PUT natasha agency", st)
if isinstance(out, dict):
    print(" roles", out.get("roles"))
    print(" msg", out.get("message"))
    print(" email", out.get("email"))

print("\n--- CONFIRM ---")
for label, key, loc in [("franch", FK, FLOC), ("franq", KEY, LOC)]:
    st, n, hits = listed(key, loc, "natashasouza.gestora@gmail.com")
    print(label, "natasha", st, "n=", n, [(h.get("id"), h.get("name"), (h.get("roles") or {}).get("role")) for h in hits])
    st, n, hits = listed(key, loc, FILIPE)
    print(label, "filipe", st, [(h.get("id"), h.get("email"), (h.get("roles") or {}).get("locationIds")) for h in hits])
