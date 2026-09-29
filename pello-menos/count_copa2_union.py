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
KEY = vals["GHL_PELLO_API_KEY"]
LOC = vals["GHL_PELLO_LOCATION_ID"]
BASE = "https://services.leadconnectorhq.com"
GER = "aT17W0Ji0S4uspb9nvZ7"
UNI = "Z4shUI5dGN5lZGYPKc78"


def req(body):
    data = json.dumps(body).encode()
    r = urllib.request.Request(
        BASE + "/contacts/search",
        data=data,
        method="POST",
        headers={
            "Authorization": "Bearer " + KEY,
            "Version": "2021-07-28",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0",
        },
    )
    with urllib.request.urlopen(r, timeout=90) as resp:
        return json.loads(resp.read().decode())


def all_ids(field, op, uid):
    ids = []
    page = 1
    total = None
    while True:
        d = req(
            {
                "locationId": LOC,
                "page": page,
                "pageLimit": 100,
                "filters": [{"field": field, "operator": op, "value": uid}],
            }
        )
        batch = d.get("contacts") or []
        total = d.get("total")
        ids.extend(c.get("id") for c in batch)
        if not batch or len(ids) >= (total or 0) or page > 20:
            break
        page += 1
    return set(ids), total


owner_ger, t1 = all_ids("assignedTo", "eq", GER)
owner_uni, t2 = all_ids("assignedTo", "eq", UNI)
fol_ger, t3 = all_ids("followers", "eq", GER)
fol_uni, t4 = all_ids("followers", "eq", UNI)
union = owner_ger | owner_uni | fol_ger | fol_uni
both = owner_uni & fol_ger
print("proprietario gerencia", len(owner_ger), "api", t1)
print("proprietario unidade", len(owner_uni), "api", t2)
print("seguidor gerencia", len(fol_ger), "api", t3)
print("seguidor unidade", len(fol_uni), "api", t4)
print("unidade dono E gerencia seguidora", len(both))
print("so gerencia dona, fora dos outros", len(owner_ger - owner_uni - fol_ger - fol_uni))
print("UNIAO proprietario ou seguidor", len(union))
