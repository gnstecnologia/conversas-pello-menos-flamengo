# -*- coding: utf-8 -*-
"""Garante Natasha Souza admin na Pello Menos | Franqueadora."""
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

FK = vals["GHL_PELLO_API_KEY"]
FLOC = vals["GHL_PELLO_LOCATION_ID"]
KEY = vals["GHL_PELLO_FRANQ_API_KEY"]
LOC = vals["GHL_PELLO_FRANQ_LOCATION_ID"]
COMPANY = "PIK3OmRl8Y7U0cy1tHSR"
EMAIL = "natashasouza.gestora@gmail.com"
PASSWORD = "Pello@2026"


def req(key, method, url, body=None):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    r = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {key}",
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


def list_users(key, loc):
    code, data = req(key, "GET", f"https://services.leadconnectorhq.com/users/?locationId={loc}")
    users = (data or {}).get("users") or [] if isinstance(data, dict) else []
    print("LIST", loc, code, len(users) if isinstance(users, list) else data)
    return users if isinstance(users, list) else []


def get_user(key, uid):
    code, data = req(key, "GET", f"https://services.leadconnectorhq.com/users/{uid}")
    u = data
    if isinstance(data, dict):
        u = data.get("user") or data.get("data") or data
    print("GET", uid, code, (u.get("email") if isinstance(u, dict) else str(u)[:200]))
    return u if isinstance(u, dict) else {}


def full_admin_perms(existing):
    perms = dict(existing or {})
    for k, v in list(perms.items()):
        if not isinstance(v, bool):
            continue
        name = k.lower()
        if "readonly" in name or name == "assigneddataonly":
            perms[k] = False
        else:
            perms[k] = True
    defaults = {
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
    for k, v in defaults.items():
        perms.setdefault(k, v)
    return perms


franq_users = list_users(KEY, LOC)
franch_users = list_users(FK, FLOC)

hit_franq = next((u for u in franq_users if (u.get("email") or "").lower() == EMAIL), None)
hit_franch = next((u for u in franch_users if (u.get("email") or "").lower() == EMAIL), None)
print("on franq", bool(hit_franq), "on franchising", bool(hit_franch))
if hit_franch:
    print("franchising user", hit_franch.get("id"), hit_franch.get("name"), (hit_franch.get("roles") or {}))

if hit_franq:
    uid = hit_franq["id"]
    cur = get_user(KEY, uid)
    body = {
        "companyId": COMPANY,
        "firstName": cur.get("firstName") or "Natasha",
        "lastName": cur.get("lastName") or "Souza",
        "type": "account",
        "role": "admin",
        "locationIds": [LOC],
        "permissions": full_admin_perms(cur.get("permissions") or hit_franq.get("permissions")),
    }
    c, b = req(KEY, "PUT", f"https://services.leadconnectorhq.com/users/{uid}", body)
    print("PUT existing franq", c, str(b)[:400] if not isinstance(b, dict) else (b.get("email") or (b.get("roles") or {})))
else:
    src = None
    src_key = None
    if hit_franch:
        src = get_user(FK, hit_franch["id"])
        src_key = FK
        print("will try add location to existing Natasha", hit_franch["id"])
        locs = list((src.get("roles") or {}).get("locationIds") or [FLOC])
        # Franqueadora token só enxerga LOC; Franchising token só FLOC.
        body_fr = {
            "companyId": COMPANY,
            "firstName": src.get("firstName") or "Natasha",
            "lastName": src.get("lastName") or "Souza",
            "type": "account",
            "role": "admin",
            "locationIds": [LOC],
            "permissions": full_admin_perms(src.get("permissions") or hit_franch.get("permissions")),
        }
        c, b = req(KEY, "PUT", f"https://services.leadconnectorhq.com/users/{hit_franch['id']}", body_fr)
        print("PUT franq-token add loc", c, str(b)[:500] if not isinstance(b, dict) else json.dumps(
            {"email": b.get("email"), "id": b.get("id"), "roles": b.get("roles"), "message": b.get("message")},
            ensure_ascii=False,
        )[:500])
        if c not in (200, 201):
            body_fs = dict(body_fr)
            body_fs["locationIds"] = list(dict.fromkeys(locs + [LOC]))
            c2, b2 = req(FK, "PUT", f"https://services.leadconnectorhq.com/users/{hit_franch['id']}", body_fs)
            print("PUT franch-token add loc", c2, str(b2)[:500] if not isinstance(b2, dict) else json.dumps(
                {"email": b2.get("email"), "id": b2.get("id"), "roles": b2.get("roles"), "message": b2.get("message")},
                ensure_ascii=False,
            )[:500])

    still = next((u for u in list_users(KEY, LOC) if (u.get("email") or "").lower() == EMAIL), None)
    if not still:
        print("CREATE on franq")
        body = {
            "firstName": (src or {}).get("firstName") or "Natasha",
            "lastName": (src or {}).get("lastName") or "Souza",
            "email": EMAIL,
            "password": PASSWORD,
            "type": "account",
            "role": "admin",
            "locationIds": [LOC],
            "permissions": full_admin_perms((src or {}).get("permissions")),
            "companyId": COMPANY,
        }
        c, b = req(KEY, "POST", "https://services.leadconnectorhq.com/users/", body)
        print("POST", c)
        if isinstance(b, dict):
            print(json.dumps(
                {k: b.get(k) for k in ("id", "email", "name", "message", "error", "statusCode", "traceId")},
                ensure_ascii=False,
                indent=2,
            ))
            user = b.get("user") or b
            print("created", user.get("id"), user.get("email"), (user.get("roles") or {}).get("role"))
        else:
            print(str(b)[:800])

print("--- AFTER FRANQ ---")
for u in list_users(KEY, LOC):
    em = (u.get("email") or "").lower()
    mark = " <<<" if em == EMAIL or "natasha" in (u.get("name") or "").lower() else ""
    print(u.get("id"), "|", u.get("name"), "|", u.get("email"), "|", (u.get("roles") or {}).get("role"), mark)
