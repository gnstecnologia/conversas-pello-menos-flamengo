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

URG_K = vals["GHL_PELLO_URG_API_KEY"]
URG_L = vals["GHL_PELLO_URG_LOCATION_ID"]
LBI_K = vals["GHL_PELLO_MODELO_API_KEY"]
LBI_L = vals["GHL_PELLO_MODELO_LOCATION_ID"]
FK = vals["GHL_PELLO_API_KEY"]
FLOC = vals["GHL_PELLO_LOCATION_ID"]
AGENCY = vals.get("GHL_AGENCY_API_KEY")


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
        with urllib.request.urlopen(r, timeout=40) as resp:
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"raw": raw[:300]}


print("=== URG DEST ===")
st, d = req(URG_K, "GET", "https://services.leadconnectorhq.com/locations/" + URG_L)
L = d.get("location") or d
print("loc", st, L.get("name"), L.get("id"))
st, d = req(URG_K, "POST", "https://services.leadconnectorhq.com/contacts/search", {"locationId": URG_L, "pageLimit": 1})
print("contacts", st, d.get("total") if isinstance(d, dict) else d)
st, d = req(URG_K, "GET", "https://services.leadconnectorhq.com/opportunities/search?location_id=" + URG_L + "&limit=1")
print("opps", st, (d.get("meta") or {}).get("total") if isinstance(d, dict) else d)

print("\n=== LBI DEST ===")
for label, tok in (("PIT", LBI_K), ("AGENCY", AGENCY)):
    if not tok:
        continue
    st, d = req(tok, "GET", "https://services.leadconnectorhq.com/locations/" + LBI_L)
    L = d.get("location") or d if isinstance(d, dict) else {}
    print(label, st, L.get("name") if isinstance(L, dict) else d)

st, d = req(LBI_K, "POST", "https://services.leadconnectorhq.com/contacts/search", {"locationId": LBI_L, "pageLimit": 1})
print("LBI contacts PIT", st, d if st != 200 else d.get("total"))
st, d = req(LBI_K, "GET", "https://services.leadconnectorhq.com/opportunities/pipelines?locationId=" + LBI_L)
print("LBI pipes PIT", st, str(d)[:200])
