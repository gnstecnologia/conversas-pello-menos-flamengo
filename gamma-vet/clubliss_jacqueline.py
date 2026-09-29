# -*- coding: utf-8 -*-
"""Lista usuários ClubLiss e cria/atualiza Jacqueline Souza."""
from __future__ import annotations

import json
import secrets
import string
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ENV = Path(r"c:\Users\GC1\Desktop\Automação GHL\.env")
OUT = Path(r"c:\Users\GC1\Desktop\Automação GHL\gamma-vet")
vals = {}
for line in ENV.read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()

KEY = vals["GHL_CLUBLISS_API_KEY"]
LOC = vals["GHL_CLUBLISS_LOCATION_ID"]
COMPANY = "PIK3OmRl8Y7U0cy1tHSR"
TARGET_EMAIL = "cl.adm@clubliss.com.br"
FIRST = "Jacqueline"
LAST = "Souza"


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


def list_users():
    code, data = req("GET", f"https://services.leadconnectorhq.com/users/?locationId={LOC}")
    users = (data or {}).get("users") or [] if isinstance(data, dict) else []
    print("LIST", code, "n=", len(users))
    return users


def get_user(uid):
    code, data = req("GET", f"https://services.leadconnectorhq.com/users/{uid}")
    if isinstance(data, dict):
        return data.get("user") or data.get("data") or data
    return {}


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
    }
    for k, v in defaults.items():
        perms.setdefault(k, v)
    return perms


def make_password():
    alphabet = string.ascii_letters + string.digits
    return "Cl@" + "".join(secrets.choice(alphabet) for _ in range(10))


def main():
    users = list_users()
    (OUT / "clubliss-users-before.json").write_text(
        json.dumps(users, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    for u in users:
        roles = u.get("roles") or {}
        print(
            u.get("id"),
            "|",
            u.get("name"),
            "|",
            u.get("email"),
            "|",
            "role=",
            roles.get("role"),
            "type=",
            roles.get("type"),
        )

    by_email = {(u.get("email") or "").lower(): u for u in users}

    def name_of(u):
        return ((u.get("name") or "") + " " + (u.get("firstName") or "") + " " + (u.get("lastName") or "")).lower()

    jacs = [
        u
        for u in users
        if "jacqueline" in name_of(u) or "jacqueline" in (u.get("email") or "").lower()
    ]
    email_hit = by_email.get(TARGET_EMAIL.lower())
    print("MATCH email", bool(email_hit), "MATCH name", [(x.get("id"), x.get("name"), x.get("email")) for x in jacs])

    target = email_hit or (jacs[0] if jacs else None)
    password = make_password()

    if target:
        uid = target["id"]
        cur = get_user(uid)
        print("UPDATE", uid, cur.get("email"), cur.get("name"))
        body = {
            "companyId": COMPANY,
            "firstName": FIRST,
            "lastName": LAST,
            "type": "account",
            "role": "admin",
            "locationIds": [LOC],
            "permissions": full_admin_perms(cur.get("permissions") or target.get("permissions")),
            "password": password,
        }
        # tentativa 1: sem email (API costuma recusar troca)
        c, b = req("PUT", f"https://services.leadconnectorhq.com/users/{uid}", body)
        print("PUT no-email", c, str(b)[:400] if not isinstance(b, dict) else (b.get("email") or b.get("message") or b.get("id") or list(b.keys())[:8]))
        if (cur.get("email") or "").lower() != TARGET_EMAIL:
            body2 = dict(body)
            body2["email"] = TARGET_EMAIL
            c2, b2 = req("PUT", f"https://services.leadconnectorhq.com/users/{uid}", body2)
            print("PUT with-email", c2, str(b2)[:400] if not isinstance(b2, dict) else (b2.get("email") or b2.get("message") or list(b2.keys())[:8]))
    else:
        print("CREATE", TARGET_EMAIL)
        body = {
            "firstName": FIRST,
            "lastName": LAST,
            "email": TARGET_EMAIL,
            "password": password,
            "type": "account",
            "role": "admin",
            "locationIds": [LOC],
            "permissions": full_admin_perms({}),
            "companyId": COMPANY,
        }
        c, b = req("POST", "https://services.leadconnectorhq.com/users/", body)
        print("POST", c, str(b)[:500] if not isinstance(b, dict) else json.dumps(
            {k: b.get(k) for k in ("id", "email", "name", "message", "error", "statusCode")},
            ensure_ascii=False,
        ))
        (OUT / "clubliss-jacqueline-create.json").write_text(
            json.dumps(b, ensure_ascii=False, indent=2) if isinstance(b, dict) else str(b),
            encoding="utf-8",
        )

    users2 = list_users()
    (OUT / "clubliss-users-after.json").write_text(
        json.dumps(users2, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("--- AFTER ---")
    for u in users2:
        roles = u.get("roles") or {}
        mark = ""
        em = (u.get("email") or "").lower()
        if em == TARGET_EMAIL or "jacqueline" in name_of(u):
            mark = " <<<"
        print(u.get("id"), "|", u.get("name"), "|", u.get("email"), "|", roles.get("role"), mark)

    print("PASSWORD", password)


if __name__ == "__main__":
    main()
