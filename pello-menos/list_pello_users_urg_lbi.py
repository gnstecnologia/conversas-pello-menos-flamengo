# -*- coding: utf-8 -*-
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

accounts = [
    ("Franchising", vals.get("GHL_PELLO_API_KEY"), vals.get("GHL_PELLO_LOCATION_ID")),
    ("URG", vals.get("GHL_PELLO_URG_API_KEY"), vals.get("GHL_PELLO_URG_LOCATION_ID")),
    ("LBI", vals.get("GHL_PELLO_MODELO_API_KEY"), vals.get("GHL_PELLO_MODELO_LOCATION_ID")),
]
for name, key, loc in accounts:
    print("===", name, loc)
    if not key or not loc:
        print("  missing key/loc")
        continue
    try:
        r = urllib.request.Request(
            "https://services.leadconnectorhq.com/users/?locationId=" + loc,
            headers={
                "Authorization": "Bearer " + key,
                "Version": "2021-07-28",
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0",
            },
        )
        with urllib.request.urlopen(r, timeout=40) as resp:
            d = json.loads(resp.read().decode() or "{}")
        for u in d.get("users") or []:
            role = u.get("roles") or {}
            rtype = role.get("role") if isinstance(role, dict) else role
            print(
                " ",
                u.get("id"),
                "|",
                u.get("email"),
                "|",
                (u.get("firstName") or ""),
                (u.get("lastName") or ""),
                "|",
                rtype,
            )
    except urllib.error.HTTPError as e:
        print("  ERR", e.code, e.read()[:200].decode(errors="replace"))
