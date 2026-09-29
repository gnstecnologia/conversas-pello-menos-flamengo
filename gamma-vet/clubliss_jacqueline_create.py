# -*- coding: utf-8 -*-
"""Cria acesso Jacqueline Souza com cl.adm@clubliss.com.br (API nao troca email)."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ENV = Path(r"c:\Users\GC1\Desktop\Automação GHL\.env")
vals = {}
for line in ENV.read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()

KEY = vals["GHL_CLUBLISS_API_KEY"]
LOC = vals["GHL_CLUBLISS_LOCATION_ID"]
COMPANY = "PIK3OmRl8Y7U0cy1tHSR"
OLD_ID = "x3gkG5FzkI08UueLurki"
EMAIL = "cl.adm@clubliss.com.br"
PASSWORD = "Clubliss@2026"


def req(method, url, body=None):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    r = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {KEY}",
            "Version": "2021-07-28",
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "Mozilla/5.0",
        },
    )
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = raw
        return e.code, parsed


code, old = req("GET", f"https://services.leadconnectorhq.com/users/{OLD_ID}")
print("GET old", code)
if isinstance(old, dict) and "permissions" not in old and isinstance(old.get("user"), dict):
    old = old["user"]
perms = old.get("permissions") if isinstance(old, dict) else {}
print("old email", old.get("email") if isinstance(old, dict) else None)
print("perms keys", len(perms) if isinstance(perms, dict) else perms)

if not isinstance(perms, dict) or not perms:
    perms = {
        "campaignsEnabled": True,
        "contactsEnabled": True,
        "workflowsEnabled": True,
        "triggersEnabled": True,
        "funnelsEnabled": True,
        "websitesEnabled": True,
        "opportunitiesEnabled": True,
        "dashboardStatsEnabled": True,
        "bulkRequestsEnabled": True,
        "appointmentsEnabled": True,
        "reviewsEnabled": True,
        "onlineListingsEnabled": True,
        "phoneCallEnabled": True,
        "conversationsEnabled": True,
        "assignedDataOnly": False,
        "settingsEnabled": True,
        "tagsEnabled": True,
        "marketingEnabled": True,
        "botService": True,
        "contentAiEnabled": True,
        "paymentsEnabled": True,
        "communitiesEnabled": True,
        "invoiceEnabled": True,
        "socialPlanner": True,
    }

body = {
    "firstName": "Jacqueline",
    "lastName": "Souza",
    "email": EMAIL,
    "password": PASSWORD,
    "type": "account",
    "role": "admin",
    "locationIds": [LOC],
    "permissions": perms,
    "companyId": COMPANY,
}
c, b = req("POST", "https://services.leadconnectorhq.com/users/", body)
print("POST", c)
if isinstance(b, dict):
    print(json.dumps({k: b.get(k) for k in ("id", "email", "name", "message", "error", "statusCode", "traceId")}, ensure_ascii=False, indent=2))
    user = b.get("user") or b
    print("created id", user.get("id"), "email", user.get("email"), "role", (user.get("roles") or {}).get("role"))
else:
    print(str(b)[:800])

c2, data = req("GET", f"https://services.leadconnectorhq.com/users/?locationId={LOC}")
users = (data or {}).get("users") or [] if isinstance(data, dict) else []
print("AFTER count", c2, len(users))
for u in users:
    em = (u.get("email") or "").lower()
    if "jacqueline" in (u.get("name") or "").lower() or em in (EMAIL, "recrutamentoclubliss@gmail.com"):
        print(" ", u.get("id"), u.get("name"), u.get("email"), (u.get("roles") or {}).get("role"))
