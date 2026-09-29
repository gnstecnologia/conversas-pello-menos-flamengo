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


def req(method, url, body=None):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode()
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
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")[:400]


st, d = req("GET", BASE + "/users/?locationId=" + LOC)
users = d.get("users") or []
print("=== USUARIOS FRANCHISING com URG / URUGUAI ===")
urg_users = []
for u in users:
    blob = " ".join(
        [
            u.get("id") or "",
            u.get("email") or "",
            u.get("firstName") or "",
            u.get("lastName") or "",
            u.get("name") or "",
        ]
    ).lower()
    if any(x in blob for x in ("urg", "uruguai", "snp")):
        role = (u.get("roles") or {}).get("role") if isinstance(u.get("roles"), dict) else u.get("roles")
        print(
            u.get("id"),
            "|",
            u.get("email"),
            "|",
            (u.get("firstName") or ""),
            (u.get("lastName") or ""),
            "|",
            role,
        )
        urg_users.append(u)

print("\n=== TODOS OS USUARIOS (para conferir par gerencia/unidade) ===")
for u in sorted(users, key=lambda x: ((x.get("firstName") or "") + (x.get("lastName") or "")).lower()):
    role = (u.get("roles") or {}).get("role") if isinstance(u.get("roles"), dict) else ""
    print(
        f"{(u.get('firstName') or '')} {(u.get('lastName') or '')} | {u.get('email')} | {u.get('id')} | {role}"
    )

# recount all contacts by assignedTo
print("\n=== CONTAGEM POR PROPRIETARIO (todos) ===")
counts = Counter()
urg_extra = []
page = 1
total_seen = 0
urg_ids = {u.get("id") for u in urg_users}
while True:
    st, data = req(
        "POST",
        BASE + "/contacts/search",
        {"locationId": LOC, "page": page, "pageLimit": 100},
    )
    batch = data.get("contacts") or []
    for c in batch:
        owner = c.get("assignedTo") or "(sem)"
        counts[owner] += 1
        blob = " ".join(
            [
                c.get("contactName") or "",
                c.get("name") or "",
                c.get("source") or "",
                " ".join(c.get("tags") or []),
            ]
        ).lower()
        if owner in urg_ids or "uruguai" in blob or "urg" in blob:
            urg_extra.append(
                {
                    "id": c.get("id"),
                    "name": c.get("contactName") or c.get("name"),
                    "assignedTo": owner,
                    "phone": c.get("phone"),
                    "hint": blob[:80],
                }
            )
        total_seen += 1
    total = data.get("total") or 0
    if not batch or total_seen >= total:
        break
    page += 1
    if page > 80:
        break

user_map = {
    u.get("id"): f"{u.get('firstName') or ''} {u.get('lastName') or ''} <{u.get('email')}>"
    for u in users
}
print("contatos totais", total_seen)
print("\n--- so URG / URUGUAI ---")
urg_total = 0
for uid in urg_ids:
    n = counts.get(uid, 0)
    urg_total += n
    print(n, "|", user_map.get(uid, uid))
print("SOMA assignedTo URG", urg_total)

# contacts mentioning uruguai but other owner
other = [c for c in urg_extra if c["assignedTo"] not in urg_ids]
print("mencionam uruguai mas outro dono", len(other))
for c in other[:20]:
    print(" ", user_map.get(c["assignedTo"], c["assignedTo"]), "|", c["name"], "|", c["phone"])

print("\n--- opps assigned_to cada URG user ---")
for uid in urg_ids:
    st, d = req(
        "GET",
        f"{BASE}/opportunities/search?location_id={LOC}&assigned_to={uid}&limit=100",
    )
    opps = d.get("opportunities") if isinstance(d, dict) else []
    print(user_map.get(uid, uid), "opps", len(opps) if isinstance(opps, list) else st, str(d)[:80] if not isinstance(opps, list) else "")
