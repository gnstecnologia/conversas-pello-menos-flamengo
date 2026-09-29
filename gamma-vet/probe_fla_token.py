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
BASE = "https://services.leadconnectorhq.com"
KEY = vals["GHL_AGENCY_API_KEY"]
body = json.dumps(
    {"companyId": vals["GHL_AGENCY_COMPANY_ID"], "locationId": "NVole6OHB4Zwe7WtjXAA"}
).encode()
r = urllib.request.Request(
    BASE + "/oauth/locationToken",
    data=body,
    method="POST",
    headers={
        "Authorization": "Bearer " + KEY,
        "Version": "2021-07-28",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
    },
)
try:
    with urllib.request.urlopen(r, timeout=45) as resp:
        data = json.loads(resp.read().decode())
except urllib.error.HTTPError as e:
    print("ERR", e.code, e.read().decode(errors="replace")[:400])
    raise SystemExit(1)
print("keys", list(data))
token = data.get("access_token") or data.get("accessToken")
print("has_token", bool(token), "location", data.get("locationId"))
if token:
    r2 = urllib.request.Request(
        BASE + "/contacts/search",
        data=json.dumps({"locationId": "NVole6OHB4Zwe7WtjXAA", "page": 1, "pageLimit": 1}).encode(),
        method="POST",
        headers={
            "Authorization": "Bearer " + token,
            "Version": "2021-07-28",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0",
        },
    )
    try:
        with urllib.request.urlopen(r2, timeout=45) as resp:
            d = json.loads(resp.read().decode())
        print("contacts", resp.status, d.get("total"))
    except urllib.error.HTTPError as e:
        print("contacts ERR", e.code, e.read().decode(errors="replace")[:250])
