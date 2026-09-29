# -*- coding: utf-8 -*-
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

ACCOUNTS = [
    ("FRANCHISING", vals["GHL_PELLO_API_KEY"], vals["GHL_PELLO_LOCATION_ID"]),
    ("URUGUAI", vals["GHL_PELLO_URG_API_KEY"], vals["GHL_PELLO_URG_LOCATION_ID"]),
    ("MODELO", vals["GHL_PELLO_MODELO_API_KEY"], vals["GHL_PELLO_MODELO_LOCATION_ID"]),
]


def req(key, url, ver="2021-07-28"):
    r = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {key}",
            "Version": ver,
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
        },
    )
    try:
        with urllib.request.urlopen(r, timeout=45) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")[:300]


for label, key, loc in ACCOUNTS:
    st, data = req(key, f"https://services.leadconnectorhq.com/locations/{loc}")
    name = ""
    if isinstance(data, dict):
        L = data.get("location") or data
        name = L.get("name") if isinstance(L, dict) else ""
    print(f"\n=== {label} {loc} {name} locHTTP={st} ===")
    st, data = req(key, f"https://services.leadconnectorhq.com/users/?locationId={loc}")
    users = (data or {}).get("users") or [] if isinstance(data, dict) else []
    print("users", st, len(users) if isinstance(users, list) else data)
    if isinstance(users, list):
        for u in users:
            roles = u.get("roles") or {}
            print(
                " ",
                u.get("name"),
                "|",
                u.get("email"),
                "|",
                roles.get("role"),
                roles.get("type"),
            )
