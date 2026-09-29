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
USERS = {
    "aT17W0Ji0S4uspb9nvZ7": "gerencia acpaula_9@hotmail.com",
    "Z4shUI5dGN5lZGYPKc78": "unidade scl@pellomenos.com.br",
}


def req(method, url, body=None):
    data = None if body is None else json.dumps(body).encode()
    headers = {
        "Authorization": "Bearer " + KEY,
        "Version": "2021-07-28",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    r = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(r, timeout=90) as resp:
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")[:500]


st, d = req("POST", BASE + "/contacts/search", {"locationId": LOC, "page": 1, "pageLimit": 1})
print("sample", st, "total", d.get("total") if isinstance(d, dict) else d)
c0 = (d.get("contacts") or [None])[0] if isinstance(d, dict) else None
if isinstance(c0, dict):
    print("keys", sorted(c0.keys()))
    print("assignedTo", c0.get("assignedTo"))
    print("followers", c0.get("followers"))

for uid, label in USERS.items():
    for field, op in (("assignedTo", "eq"), ("followers", "eq"), ("followers", "contains")):
        body = {
            "locationId": LOC,
            "page": 1,
            "pageLimit": 1,
            "filters": [{"field": field, "operator": op, "value": uid}],
        }
        st, data = req("POST", BASE + "/contacts/search", body)
        total = data.get("total") if isinstance(data, dict) else None
        print(label, field, op, st, "total", total, "err", "" if isinstance(data, dict) and "contacts" in data else str(data)[:180])
