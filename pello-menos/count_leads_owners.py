# -*- coding: utf-8 -*-
import json
import sys
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
vals = {}
for line in Path(r"c:\Users\GC1\Desktop\Automação GHL\.env").read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()
BASE = "https://services.leadconnectorhq.com"


def opp_total(key, loc, uid):
    url = f"{BASE}/opportunities/search?location_id={loc}&assigned_to={uid}&limit=1"
    r = urllib.request.Request(
        url,
        headers={
            "Authorization": "Bearer " + key,
            "Version": "2021-07-28",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
        },
    )
    with urllib.request.urlopen(r, timeout=60) as resp:
        d = json.loads(resp.read().decode())
    return (d.get("meta") or {}).get("total")


def contact_total(key, loc, uid):
    body = json.dumps(
        {
            "locationId": loc,
            "page": 1,
            "pageLimit": 1,
            "filters": [{"field": "assignedTo", "operator": "eq", "value": uid}],
        }
    ).encode()
    r = urllib.request.Request(
        BASE + "/contacts/search",
        data=body,
        method="POST",
        headers={
            "Authorization": "Bearer " + key,
            "Version": "2021-07-28",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0",
        },
    )
    with urllib.request.urlopen(r, timeout=60) as resp:
        return json.loads(resp.read().decode()).get("total")


FK = vals["GHL_PELLO_API_KEY"]
FLOC = vals["GHL_PELLO_LOCATION_ID"]
checks = [
    ("COPA2 franch unidade", FK, FLOC, "Z4shUI5dGN5lZGYPKc78"),
    ("COPA2 dest paula", vals["GHL_PELLO_COPA2_API_KEY"], vals["GHL_PELLO_COPA2_LOCATION_ID"], "zlrDitDis11sjRKqJWDS"),
    ("FLA franch unidade", FK, FLOC, "y3WSdOwVSPCzyw59wk1Y"),
    ("FLA dest fla", vals["GHL_PELLO_FLA_API_KEY"], vals["GHL_PELLO_FLA_LOCATION_ID"], "y3WSdOwVSPCzyw59wk1Y"),
    ("SJC franch unidade", FK, FLOC, "xHPu5HbnVNPF6QuPnf73"),
]
for label, key, loc, uid in checks:
    print(label, "leads", opp_total(key, loc, uid), "contatos", contact_total(key, loc, uid))
