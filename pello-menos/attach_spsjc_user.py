# -*- coding: utf-8 -*-
"""Liga sp-sjc@ na subconta SP-SJC com as restrições da URG/COPA2/FLA."""
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
DK = vals["GHL_PELLO_SPSJC_API_KEY"]
DLOC = vals["GHL_PELLO_SPSJC_LOCATION_ID"]
AG = vals["GHL_AGENCY_API_KEY"]
COMPANY = vals["GHL_AGENCY_COMPANY_ID"]
UID = "xHPu5HbnVNPF6QuPnf73"
EMAIL = "sp-sjc@pellomenos.com.br"
BASE = "https://services.leadconnectorhq.com"
TEMPLATE = json.loads(
    Path(r"c:\Users\GC1\Desktop\Automação GHL\pello-menos\snp-user-template.json").read_text(encoding="utf-8")
)


def req(token, method, url, body=None):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    headers = {
        "Authorization": "Bearer " + token,
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


st, cur = req(FK, "GET", BASE + "/users/" + UID)
user = cur.get("user") or cur
roles = user.get("roles") or {}
locs = list(dict.fromkeys((roles.get("locationIds") or [FLOC]) + [DLOC]))
print("GET", st, user.get("email"), roles.get("role"), roles.get("locationIds"))

body = {
    "companyId": COMPANY,
    "firstName": user.get("firstName") or "Unidade",
    "lastName": user.get("lastName") or "São José dos Campos",
    "email": EMAIL,
    "password": "@Genesis12345SPSJC",
    "type": "account",
    "role": "user",
    "locationIds": locs,
    "permissions": TEMPLATE["permissions"],
    "scopes": TEMPLATE.get("scopes"),
    "scopesAssignedToOnly": TEMPLATE.get("scopesAssignedToOnly"),
}
ok = None
for label, token in (("agency", AG), ("franch", FK), ("spsjc", DK)):
    st, out = req(token, "PUT", BASE + "/users/" + UID, body)
    msg = ""
    if isinstance(out, dict):
        msg = out.get("message") or out.get("email") or ""
    print("PUT", label, st, msg)
    if st in (200, 201):
        ok = out.get("user") or out
        break

st, users = req(DK, "GET", BASE + "/users/?locationId=" + DLOC)
print("users on SPSJC", st)
found = None
if isinstance(users, dict):
    for u in users.get("users") or []:
        print(" ", u.get("email"), u.get("id"), (u.get("roles") or {}).get("role"))
        if (u.get("email") or "").lower() == EMAIL:
            found = u

st, cur = req(AG, "GET", BASE + "/users/" + UID)
u = (cur.get("user") or cur) if isinstance(cur, dict) else {}
p = u.get("permissions") or {}
roles = u.get("roles") or {}
print("email", u.get("email"))
print("locations", roles.get("locationIds"))
print("na_subconta", DLOC in (roles.get("locationIds") or []), "found_list", bool(found))
print(
    "assignedDataOnly",
    p.get("assignedDataOnly"),
    "opportunities",
    p.get("opportunitiesEnabled"),
    "conversations",
    p.get("conversationsEnabled"),
    "contacts",
    p.get("contactsEnabled"),
    "workflows",
    p.get("workflowsEnabled"),
    "campaigns",
    p.get("campaignsEnabled"),
    "settings",
    p.get("settingsEnabled"),
    "appointments",
    p.get("appointmentsEnabled"),
    "marketing",
    p.get("marketingEnabled"),
    "dashboard",
    p.get("dashboardStatsEnabled"),
    "phone",
    p.get("phoneCallEnabled"),
)
if not found:
    raise SystemExit(1)
