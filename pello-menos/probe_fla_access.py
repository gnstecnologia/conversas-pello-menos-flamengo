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
LOC = "NVole6OHB4Zwe7WtjXAA"
BASE = "https://services.leadconnectorhq.com"


def call(key, method, path, body=None):
    data = None if body is None else json.dumps(body).encode()
    headers = {
        "Authorization": "Bearer " + key,
        "Version": "2021-07-28",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    r = urllib.request.Request(BASE + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(r, timeout=45) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")[:220]


for label, key in (("agency", vals["GHL_AGENCY_API_KEY"]), ("franch", vals["GHL_PELLO_API_KEY"])):
    st, d = call(key, "GET", "/locations/" + LOC)
    name = (d.get("location") or d).get("name") if isinstance(d, dict) else ""
    print(label, "location", st, name or str(d)[:120])
    st, d = call(key, "POST", "/contacts/search", {"locationId": LOC, "page": 1, "pageLimit": 1})
    print(label, "contacts", st, d.get("total") if isinstance(d, dict) else str(d)[:120])
