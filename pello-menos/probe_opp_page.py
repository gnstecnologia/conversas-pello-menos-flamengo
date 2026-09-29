# -*- coding: utf-8 -*-
import json, sys, urllib.request, urllib.error
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
vals = {}
for line in Path(r"c:\Users\GC1\Desktop\Automação GHL\.env").read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()
KEY = vals["GHL_PELLO_API_KEY"]
LOC = vals["GHL_PELLO_LOCATION_ID"]
OLD_K = vals["GHL_PELLO_URUGUAI_OLD_API_KEY"]
OLD_L = vals["GHL_PELLO_URUGUAI_OLD_LOCATION_ID"]

def req(token, url, body=None, method=None):
    data = None if body is None else json.dumps(body).encode()
    r = urllib.request.Request(
        url,
        data=data,
        method=method or ("POST" if body is not None else "GET"),
        headers={
            "Authorization": "Bearer " + token,
            "Version": "2021-07-28",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
            **({"Content-Type": "application/json"} if body is not None else {}),
        },
    )
    try:
        with urllib.request.urlopen(r, timeout=40) as resp:
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")[:300]

# first page franchising
st, d = req(KEY, f"https://services.leadconnectorhq.com/opportunities/search?location_id={LOC}&limit=20")
print("keys", list(d.keys()) if isinstance(d, dict) else d)
print("meta", d.get("meta") if isinstance(d, dict) else None)
ops = d.get("opportunities") or []
print("n", len(ops), "first", ops[0].get("id") if ops else None, "last", ops[-1].get("id") if ops else None)
if ops:
    last = ops[-1]
    print("last keys", [k for k in last if "date" in k.lower() or k in ("id",)])
    for extra in (
        f"&startAfterId={ops[-1]['id']}",
        f"&startAfter={ops[-1].get('dateAdded') or ops[-1].get('createdAt')}",
        "&skip=20",
        "&offset=20",
        "&page=2",
    ):
        st2, d2 = req(KEY, f"https://services.leadconnectorhq.com/opportunities/search?location_id={LOC}&limit=20{extra}")
        ids = [o.get("id") for o in (d2.get("opportunities") or [])] if isinstance(d2, dict) else []
        print(extra, st2, "n", len(ids), "overlap", len(set(ids) & {o['id'] for o in ops}), "meta", d2.get("meta") if isinstance(d2, dict) else str(d2)[:120])

# POST body with locationId + page
for body in (
    {"locationId": LOC, "page": 2, "pageLimit": 20, "limit": 20},
    {"locationId": LOC, "limit": 20, "skip": 20},
    {"locationId": LOC, "query": "Uruguai", "limit": 100},
):
    st, d = req(KEY, "https://services.leadconnectorhq.com/opportunities/search", body)
    n = len(d.get("opportunities") or []) if isinstance(d, dict) else 0
    print("POST", body, st, n, d.get("meta") if isinstance(d, dict) else str(d)[:150])

# old account all
st, d = req(OLD_K, f"https://services.leadconnectorhq.com/opportunities/search?location_id={OLD_L}&limit=100")
print("OLD opps", st, len(d.get("opportunities") or []) if isinstance(d, dict) else d, "meta", d.get("meta") if isinstance(d, dict) else None)
