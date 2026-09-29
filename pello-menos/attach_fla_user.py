# -*- coding: utf-8 -*-
import json
import sys
import time
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
DK = vals["GHL_PELLO_FLA_API_KEY"]
DLOC = vals["GHL_PELLO_FLA_LOCATION_ID"]
AG = vals["GHL_AGENCY_API_KEY"]
COMPANY = vals["GHL_AGENCY_COMPANY_ID"]
UID = "y3WSdOwVSPCzyw59wk1Y"
BASE = "https://services.leadconnectorhq.com"
TEMPLATE = json.loads(Path(r"c:\Users\GC1\Desktop\Automação GHL\pello-menos\snp-user-template.json").read_text(encoding="utf-8"))
RESULT = json.loads(Path(r"c:\Users\GC1\Desktop\Automação GHL\pello-menos\migrate-fla-result.json").read_text(encoding="utf-8"))


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
print("GET franch", st, user.get("email"), roles.get("role"), roles.get("locationIds"))

body = {
    "companyId": COMPANY,
    "firstName": user.get("firstName") or "Unidade",
    "lastName": user.get("lastName") or "Flamengo",
    "email": "fla@pellomenos.com.br",
    "password": "@Genesis12345FLA",
    "type": "account",
    "role": "user",
    "locationIds": list(dict.fromkeys((roles.get("locationIds") or [FLOC]) + [DLOC])),
    "permissions": TEMPLATE["permissions"],
    "scopes": TEMPLATE.get("scopes"),
    "scopesAssignedToOnly": TEMPLATE.get("scopesAssignedToOnly"),
}
for label, token in (("agency", AG), ("franch", FK), ("fla", DK)):
    st, out = req(token, "PUT", BASE + "/users/" + UID, body)
    msg = ""
    if isinstance(out, dict):
        msg = out.get("message") or out.get("email") or (out.get("roles") or {}).get("locationIds")
    print("PUT", label, st, msg)
    if st in (200, 201):
        break

st, users = req(DK, "GET", BASE + "/users/?locationId=" + DLOC)
print("users on FLA", st)
on_fla = None
if isinstance(users, dict):
    for u in users.get("users") or []:
        print(" ", u.get("email"), u.get("id"), (u.get("roles") or {}).get("role"))
        if (u.get("email") or "").lower() == "fla@pellomenos.com.br":
            on_fla = u.get("id")

if not on_fla:
    print("fla@ ainda nao esta na subconta")
    raise SystemExit(1)

assigned_c = assigned_o = 0
for row in RESULT.get("contact_results") or []:
    nid = row.get("new")
    if not nid:
        continue
    st, _ = req(DK, "PUT", BASE + "/contacts/" + nid, {"assignedTo": on_fla})
    if st in (200, 201):
        assigned_c += 1
    time.sleep(0.04)
for row in RESULT.get("opp_results") or []:
    nid = row.get("new")
    if not nid:
        continue
    st, _ = req(DK, "PUT", BASE + "/opportunities/" + nid, {"assignedTo": on_fla})
    if st in (200, 201):
        assigned_o += 1
    time.sleep(0.04)
print("assigned", assigned_c, assigned_o)

st, check = req(
    DK,
    "POST",
    BASE + "/contacts/search",
    {"locationId": DLOC, "page": 1, "pageLimit": 1, "filters": [{"field": "assignedTo", "operator": "eq", "value": on_fla}]},
)
print("search assigned", st, check.get("total") if isinstance(check, dict) else check)
st, u2 = req(DK, "GET", BASE + "/users/" + on_fla)
p = ((u2.get("user") or u2).get("permissions") or {})
print("perms", "assignedDataOnly", p.get("assignedDataOnly"), "opportunities", p.get("opportunitiesEnabled"), "contacts", p.get("contactsEnabled"), "workflows", p.get("workflowsEnabled"))
