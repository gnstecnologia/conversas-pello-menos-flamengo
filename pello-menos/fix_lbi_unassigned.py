# -*- coding: utf-8 -*-
import json, sys, urllib.request, urllib.error
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
vals = {}
for line in Path(r"c:\Users\GC1\Desktop\Automação GHL\.env").read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()
KEY = vals["GHL_PELLO_MODELO_API_KEY"]
LOC = vals["GHL_PELLO_MODELO_LOCATION_ID"]
OWNER = "tSWmqvvJyxQfDPcgeIon"

def req(method, url, body=None):
    data = None if body is None else json.dumps(body).encode()
    r = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": "Bearer " + KEY, "Version": "2021-07-28",
        "Accept": "application/json", "User-Agent": "Mozilla/5.0",
        **({"Content-Type": "application/json"} if body is not None else {}),
    })
    try:
        with urllib.request.urlopen(r, timeout=40) as resp:
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")[:300]

contacts = []
page = 1
while True:
    st, d = req("POST", "https://services.leadconnectorhq.com/contacts/search", {"locationId": LOC, "page": page, "pageLimit": 100})
    batch = d.get("contacts") or []
    contacts.extend(batch)
    if not batch or len(contacts) >= (d.get("total") or 0):
        break
    page += 1

missing = [c for c in contacts if (c.get("assignedTo") or "") != OWNER]
print("missing", len(missing), "of", len(contacts))
for c in missing:
    print(c.get("id"), c.get("contactName") or c.get("name"), c.get("phone"), "owner", c.get("assignedTo"))
    st, d = req("PUT", "https://services.leadconnectorhq.com/contacts/" + c["id"], {"assignedTo": OWNER})
    print(" PUT", st, str(d)[:180])
