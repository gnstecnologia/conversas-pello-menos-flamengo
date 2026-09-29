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

KEY = vals["GHL_PELLO_COPA2_API_KEY"]
LOC = vals["GHL_PELLO_COPA2_LOCATION_ID"]
COMPANY = vals["GHL_AGENCY_COMPANY_ID"]
UID = "zlrDitDis11sjRKqJWDS"
BASE = "https://services.leadconnectorhq.com"
TEMPLATE = json.loads(
    Path(r"c:\Users\GC1\Desktop\Automação GHL\pello-menos\snp-user-template.json").read_text(encoding="utf-8")
)


def req(method, url, body=None):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    headers = {
        "Authorization": "Bearer " + KEY,
        "Version": "2021-07-28",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0",
    }
    if body is not None:
        headers["Content-Type"] = "application/json; charset=utf-8"
    r = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"raw": raw[:400]}


st, cur = req("GET", BASE + "/users/" + UID)
user = cur.get("user") or cur
print("GET", st, user.get("email"), (user.get("roles") or {}).get("role"))
body = {
    "companyId": COMPANY,
    "firstName": user.get("firstName") or "Paula",
    "lastName": user.get("lastName") or "Copa 2",
    "email": user.get("email"),
    "password": "@Genesis12345COPA2",
    "type": "account",
    "role": "user",
    "locationIds": [LOC],
    "permissions": user.get("permissions") or TEMPLATE["permissions"],
    "scopes": user.get("scopes") or TEMPLATE.get("scopes"),
    "scopesAssignedToOnly": user.get("scopesAssignedToOnly") or TEMPLATE.get("scopesAssignedToOnly"),
}
st, out = req("PUT", BASE + "/users/" + UID, body)
print("PUT", st)
if isinstance(out, dict):
    print(out.get("email") or out.get("message") or out.get("id") or str(out)[:300])
    p = (out.get("permissions") or (out.get("user") or {}).get("permissions") or {})
    if p:
        print("assignedDataOnly", p.get("assignedDataOnly"), "opportunities", p.get("opportunitiesEnabled"))
else:
    print(str(out)[:300])
