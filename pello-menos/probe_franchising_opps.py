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
URG_UID = "0oiDGUCBjbRFs7xstVhX"
LBI_UID = "tSWmqvvJyxQfDPcgeIon"
inv = json.loads(Path(r"c:\Users\GC1\Desktop\Automação GHL\pello-menos\inventario-franchising-urg-lbi.json").read_text(encoding="utf-8"))


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
        with urllib.request.urlopen(r, timeout=40) as resp:
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")[:400]


urls = [
    f"https://services.leadconnectorhq.com/opportunities/search?location_id={LOC}&limit=20",
    f"https://services.leadconnectorhq.com/opportunities/search?location_id={LOC}&assigned_to={URG_UID}&limit=20",
    f"https://services.leadconnectorhq.com/opportunities/search?location_id={LOC}&assignedTo={URG_UID}&limit=20",
]
for u in urls:
    st, d = req("GET", u)
    print("GET", st, u.split("?")[1][:80], str(d)[:220].replace("\n", " "))

# one urg contact
cid = (inv.get("urg_contact_ids") or [None])[0]
if cid:
    st, d = req("GET", f"https://services.leadconnectorhq.com/opportunities/search?location_id={LOC}&contact_id={cid}")
    print("contact urg", cid, st, str(d)[:300].replace("\n", " "))

# POST variants
for body in (
    {"location_id": LOC, "limit": 5},
    {"locationId": LOC, "getTasks": False, "limit": 5, "query": ""},
):
    st, d = req("POST", "https://services.leadconnectorhq.com/opportunities/search", body)
    print("POST", st, body, str(d)[:220].replace("\n", " "))
