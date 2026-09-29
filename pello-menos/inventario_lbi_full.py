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

FK = vals["GHL_PELLO_API_KEY"]
FLOC = vals["GHL_PELLO_LOCATION_ID"]
LBI_K = vals["GHL_PELLO_MODELO_API_KEY"]
LBI_L = vals["GHL_PELLO_MODELO_LOCATION_ID"]
AGENCY = vals.get("GHL_AGENCY_API_KEY")
OWNERS = {"tSWmqvvJyxQfDPcgeIon", "R7zlp4VyVaqQFzhd7CGW"}


def req(token, method, url, body=None):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode()
    headers = {
        "Authorization": "Bearer " + token,
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
        raw = e.read().decode(errors="replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"raw": raw[:300]}


print("=== LBI DEST ===")
st, d = req(LBI_K, "GET", "https://services.leadconnectorhq.com/locations/" + LBI_L)
L = d.get("location") or d if isinstance(d, dict) else {}
print("PIT", st, L.get("name") if isinstance(L, dict) else d)
if st != 200 and AGENCY:
    st, d = req(AGENCY, "GET", "https://services.leadconnectorhq.com/locations/" + LBI_L)
    L = d.get("location") or d if isinstance(d, dict) else {}
    print("AGENCY", st, L.get("name") if isinstance(L, dict) else d)

st, d = req(LBI_K, "POST", "https://services.leadconnectorhq.com/contacts/search", {"locationId": LBI_L, "pageLimit": 1})
print("dest contacts", st, d.get("total") if isinstance(d, dict) else d)
st, d = req(LBI_K, "GET", "https://services.leadconnectorhq.com/opportunities/search?location_id=" + LBI_L + "&limit=1")
print("dest opps", st, (d.get("meta") or {}).get("total") if isinstance(d, dict) else d)
st, d = req(LBI_K, "GET", "https://services.leadconnectorhq.com/opportunities/pipelines?locationId=" + LBI_L)
pipes = d.get("pipelines") if isinstance(d, dict) else []
print("pipes", st, [p.get("name") for p in pipes] if isinstance(pipes, list) else d)

print("\n=== FRANCHISING LBI USERS ===")
st, d = req(FK, "GET", "https://services.leadconnectorhq.com/users/?locationId=" + FLOC)
for u in d.get("users") or []:
    blob = ((u.get("email") or "") + " " + (u.get("firstName") or "") + " " + (u.get("lastName") or "")).lower()
    if any(x in blob for x in ("lbi", "bicão", "bicao", "largo do bic")):
        print(u.get("id"), u.get("email"), u.get("firstName"), u.get("lastName"))

# assigned opps
for uid, label in (
    ("tSWmqvvJyxQfDPcgeIon", "unidade"),
    ("R7zlp4VyVaqQFzhd7CGW", "gerencia"),
):
    st, d = req(FK, "GET", f"https://services.leadconnectorhq.com/opportunities/search?location_id={FLOC}&assigned_to={uid}&limit=100")
    n = len(d.get("opportunities") or []) if isinstance(d, dict) else 0
    meta = (d.get("meta") or {}).get("total") if isinstance(d, dict) else None
    print("opps", label, st, "batch", n, "total", meta)

st, d = req(FK, "POST", "https://services.leadconnectorhq.com/opportunities/search", {"locationId": FLOC, "query": "Bicão", "limit": 100})
print("query Bicao", st, len(d.get("opportunities") or []) if isinstance(d, dict) else d)
st, d = req(FK, "POST", "https://services.leadconnectorhq.com/opportunities/search", {"locationId": FLOC, "query": "LBI", "limit": 100})
print("query LBI", st, len(d.get("opportunities") or []) if isinstance(d, dict) else d)
