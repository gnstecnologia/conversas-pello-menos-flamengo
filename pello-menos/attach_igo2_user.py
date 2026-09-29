# -*- coding: utf-8 -*-
"""Garante igo2@ na subconta IGO2 com restrições URG/COPA2/FLA."""
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
DK = vals["GHL_PELLO_IGO2_API_KEY"]
DLOC = vals["GHL_PELLO_IGO2_LOCATION_ID"]
AG = vals["GHL_AGENCY_API_KEY"]
COMPANY = vals["GHL_AGENCY_COMPANY_ID"]
UID = "q2d7GuBxMgbnh8cY1uYP"
EMAIL = "igo2@pellomenos.com.br"
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


st, cur = req(AG, "GET", BASE + "/users/" + UID)
user = cur.get("user") or cur
roles = user.get("roles") or {}
locs = list(dict.fromkeys((roles.get("locationIds") or [FLOC]) + [DLOC]))
print("GET", st, user.get("email"), roles.get("locationIds"))

body = {
    "companyId": COMPANY,
    "firstName": user.get("firstName") or "Unidade",
    "lastName": user.get("lastName") or "Ilha do Governador 2",
    "email": EMAIL,
    "password": "@Genesis12345IGO2",
    "type": "account",
    "role": "user",
    "locationIds": locs,
    "permissions": TEMPLATE["permissions"],
    "scopes": TEMPLATE.get("scopes"),
    "scopesAssignedToOnly": TEMPLATE.get("scopesAssignedToOnly"),
}
st, out = req(AG, "PUT", BASE + "/users/" + UID, body)
print("PUT agency", st, (out.get("user") or out).get("email") if isinstance(out, dict) else out)

st, cur = req(AG, "GET", BASE + "/users/" + UID)
u = cur.get("user") or cur
p = u.get("permissions") or {}
roles = u.get("roles") or {}
print("locations", roles.get("locationIds"))
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
)
st, users = req(DK, "GET", BASE + "/users/?locationId=" + DLOC)
print("users on IGO2", st, [(x.get("email"), x.get("id")) for x in (users.get("users") or [])])
