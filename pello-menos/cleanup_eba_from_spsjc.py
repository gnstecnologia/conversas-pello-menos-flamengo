# -*- coding: utf-8 -*-
"""Apaga da subconta SP-SJC só as cópias da EBA. Não altera a Franchising."""
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
vals = {}
for line in Path(r"c:\Users\GC1\Desktop\Automação GHL\.env").read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()

KEY = vals["GHL_PELLO_SPSJC_API_KEY"]
LOC = vals["GHL_PELLO_SPSJC_LOCATION_ID"]
BASE = "https://services.leadconnectorhq.com"


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
        with urllib.request.urlopen(r, timeout=60) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")[:250]


contacts = []
page = 1
while True:
    st, d = req("POST", BASE + "/contacts/search", {"locationId": LOC, "page": page, "pageLimit": 100})
    if st != 200:
        print("search", st, d)
        break
    batch = d.get("contacts") or []
    contacts.extend(batch)
    total = d.get("total") or 0
    if not batch or len(contacts) >= total:
        break
    page += 1

bad = []
for c in contacts:
    tags = [t.lower() for t in (c.get("tags") or [])]
    if "migrado_franchising" in tags or "spsjc" in tags:
        bad.append(c)
print("dest total", len(contacts), "copias EBA", len(bad))

deleted_c = deleted_o = 0
for c in bad:
    cid = c["id"]
    st, d = req("GET", f"{BASE}/opportunities/search?location_id={LOC}&contact_id={cid}&limit=20")
    for o in (d.get("opportunities") or []) if isinstance(d, dict) else []:
        so, _ = req("DELETE", BASE + "/opportunities/" + o["id"])
        if so in (200, 201):
            deleted_o += 1
        time.sleep(0.05)
    sc, _ = req("DELETE", BASE + "/contacts/" + cid)
    if sc in (200, 201):
        deleted_c += 1
    else:
        print("del contact", sc, c.get("contactName"))
    time.sleep(0.05)

print("apagados contatos", deleted_c, "leads", deleted_o)
