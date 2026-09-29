# -*- coding: utf-8 -*-
import json
import sys
import urllib.error
import urllib.request
from collections import Counter
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


def req(method, path, body=None):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    headers = {
        "Authorization": "Bearer " + KEY,
        "Version": "2021-07-28",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0",
    }
    if body is not None:
        headers["Content-Type"] = "application/json; charset=utf-8"
    r = urllib.request.Request(BASE + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"raw": raw[:400]}


st, loc = req("GET", "/locations/" + LOC)
L = loc.get("location") or loc
print("location", st, L.get("name"), L.get("id"))

st, users = req("GET", "/users/?locationId=" + LOC)
user_map = {}
for u in (users.get("users") or []) if isinstance(users, dict) else []:
    uid = u.get("id")
    label = ((u.get("firstName") or "") + " " + (u.get("lastName") or "")).strip() or u.get("name") or u.get("email")
    user_map[uid] = label + " <" + (u.get("email") or "") + ">"
    low = (label + " " + (u.get("email") or "") + " " + (u.get("name") or "")).lower()
    if any(x in low for x in ("franchis", "pello menos", "propriet", "matriz")):
        print("user match", uid, user_map[uid])

print("users total", len(user_map))

# total via search
st, first = req(
    "POST",
    "/contacts/search",
    {"locationId": LOC, "page": 1, "pageLimit": 1},
)
print("search first", st, "total", first.get("total") if isinstance(first, dict) else first)

# count by assignedTo — paginate
counts = Counter()
samples = {}
page = 1
seen = 0
while True:
    st, data = req(
        "POST",
        "/contacts/search",
        {"locationId": LOC, "page": page, "pageLimit": 100},
    )
    if st != 200 or not isinstance(data, dict):
        print("page fail", page, st, str(data)[:200])
        break
    contacts = data.get("contacts") or data.get("data") or []
    if not contacts:
        break
    for c in contacts:
        owner = c.get("assignedTo") or c.get("owner") or ""
        counts[owner or "(sem proprietario)"] += 1
        if owner not in samples:
            samples[owner] = (c.get("id"), (c.get("firstName") or "") + " " + (c.get("lastName") or ""), c.get("email"))
        seen += 1
    total = data.get("total")
    print("page", page, "seen", seen, "batch", len(contacts), "api total", total)
    if len(contacts) < 100:
        break
    if total and seen >= total:
        break
    page += 1
    if page > 200:
        print("stop at 200 pages")
        break

print("COUNTED", seen)
print("--- por proprietario ---")
for oid, n in counts.most_common():
    name = user_map.get(oid, oid)
    print(n, "|", name)

# try filter assignedTo empty / location
for filt in (
    {"assignedTo": "unassigned"},
    {"assignedTo": LOC},
    {"assignedTo": None},
):
    body = {"locationId": LOC, "page": 1, "pageLimit": 1, "filters": [{"field": "assignedTo", "operator": "eq", "value": filt["assignedTo"]}]}
    st, d = req("POST", "/contacts/search", body)
    print("filter", filt, st, (d.get("total") if isinstance(d, dict) else d))
