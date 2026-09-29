# -*- coding: utf-8 -*-
"""Corrige usuarios Gamma Vet para a lista oficial."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

ENV = Path(r"c:\Users\GC1\Desktop\Automação GHL\.env")
OUT = Path(r"c:\Users\GC1\Desktop\Automação GHL\gamma-vet\gamma-users-official.json")
vals = {}
for line in ENV.read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()

KEY = vals["GHL_GAMMA_API_KEY"]
LOC = vals["GHL_GAMMA_LOCATION_ID"]
COMPANY = "PIK3OmRl8Y7U0cy1tHSR"
PASSWORD = "@Genesis12345"

KEEP_ON = {
    "contactsEnabled": True,
    "opportunitiesEnabled": True,
    "tagsEnabled": True,
    "dashboardStatsEnabled": True,
    "appointmentsEnabled": True,
    "phoneCallEnabled": True,
    "conversationsEnabled": True,
    "botService": True,
    "agentReportingEnabled": True,
}

OFF = {
    "campaignsEnabled": False,
    "campaignsReadOnly": False,
    "workflowsEnabled": False,
    "workflowsReadOnly": False,
    "triggersEnabled": False,
    "funnelsEnabled": False,
    "websitesEnabled": False,
    "bulkRequestsEnabled": False,
    "reviewsEnabled": False,
    "onlineListingsEnabled": False,
    "assignedDataOnly": False,
    "adwordsReportingEnabled": False,
    "membershipEnabled": False,
    "facebookAdsReportingEnabled": False,
    "attributionsReportingEnabled": False,
    "settingsEnabled": False,
    "leadValueEnabled": False,
    "marketingEnabled": False,
    "socialPlanner": False,
    "bloggingEnabled": False,
    "invoiceEnabled": False,
    "affiliateManagerEnabled": False,
    "contentAiEnabled": False,
    "refundsEnabled": False,
    "recordPaymentEnabled": False,
    "cancelSubscriptionEnabled": False,
    "paymentsEnabled": False,
    "communitiesEnabled": False,
    "exportPaymentsEnabled": False,
    "adPublishingEnabled": False,
    "adPublishingReadOnly": False,
    "certificatesEnabled": False,
    "customMenuLinkReadOnly": False,
    "customMenuLinkWrite": False,
    "gokollabEnabled": False,
    "wordpressEnabled": False,
    "mediaStorageEnabled": False,
    "reportingEnabled": False,
    "opportunitiesBulkActionsEnabled": False,
}

PERMS = {**OFF, **KEEP_ON}

OFFICIAL = [
    {"firstName": "Marcello", "lastName": "Comodo", "email": "marcello.comodo@gammavet.com.br", "current": "marcello.comodo@gammavet.com.br"},
    {"firstName": "Mariana", "lastName": "Gantois", "email": "mariana.gantois@gammavet.com.br", "current": "mariana.gantois@gammavet.com.br"},
    {"firstName": "Gustavo", "lastName": "Cobucci", "email": "gustavo.cobucci@gammavet.com.br", "current": "gustavo.cobucci@gammavet.com.br"},
    {"firstName": "Marcella", "lastName": "Rosa", "email": "marcella_rosa@me.com", "current": "marcella.rosa@gammavet.com.br"},
    {"firstName": "Fernanda", "lastName": "Meirelles", "email": "nanda.meirelles1@gmail.com", "current": "fernanda.meirelles@gammavet.com.br"},
    {"firstName": "Recepcao", "lastName": "Gamma", "email": "agendamento@gammavet.com.br", "current": "agendamento@gammavet.com.br"},
]

DELETE_EMAILS = {
    "sac@gammavet.com.br",
}


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
    users = (data or {}).get("users") or []
    print("LIST", code, "n=", len(users))
    return users


def apply_user(spec, existing_by_email):
    wanted = spec["email"].lower()
    current = spec["current"].lower()
    found = existing_by_email.get(wanted) or existing_by_email.get(current)
    body_common = {
        "firstName": spec["firstName"],
        "lastName": spec["lastName"],
        "password": PASSWORD,
        "type": "account",
        "role": "user",
        "locationIds": [LOC],
        "companyId": COMPANY,
        "permissions": PERMS,
    }
    if found:
        uid = found["id"]
        print("UPDATE", found.get("email"), "->", spec["email"], uid)
        c, b = req("PUT", f"https://services.leadconnectorhq.com/users/{uid}", body_common)
        print(" PUT", c, (b.get("email") if isinstance(b, dict) else str(b)[:200]))
        # email change is often blocked; if needed, recreate
        live_email = (b.get("email") if isinstance(b, dict) else "") or found.get("email")
        if live_email and live_email.lower() != wanted:
            print(" EMAIL CHANGE BLOCKED, recreate", live_email, "->", spec["email"])
            dcode, dbody = req("DELETE", f"https://services.leadconnectorhq.com/users/{uid}")
            print(" DELETE old", dcode, str(dbody)[:180] if not isinstance(dbody, dict) else dbody)
            create = dict(body_common)
            create["email"] = spec["email"]
            c2, b2 = req("POST", "https://services.leadconnectorhq.com/users/", create)
            print(" POST new", c2, b2.get("email") if isinstance(b2, dict) else str(b2)[:200])
            return c2, b2
        return c, b
    print("CREATE", spec["email"])
    create = dict(body_common)
    create["email"] = spec["email"]
    c, b = req("POST", "https://services.leadconnectorhq.com/users/", create)
    print(" POST", c, b.get("email") if isinstance(b, dict) else str(b)[:200])
    return c, b


def main():
    users = list_users()
    by_email = {(u.get("email") or "").lower(): u for u in users}
    official_emails = {x["email"].lower() for x in OFFICIAL}

    results = []
    for spec in OFFICIAL:
        c, b = apply_user(spec, by_email)
        results.append({"email": spec["email"], "code": c, "ok": c in (200, 201)})
        users = list_users()
        by_email = {(u.get("email") or "").lower(): u for u in users}

    # delete leftovers not in official list (only account users of this location)
    leftovers = []
    for u in users:
        email = (u.get("email") or "").lower()
        role = ((u.get("roles") or {}).get("role") or "").lower()
        utype = ((u.get("roles") or {}).get("type") or "").lower()
        if email in official_emails:
            continue
        leftovers.append(u)
        print("DELETE leftover", u.get("name"), email, u.get("id"), role, utype)
        dcode, dbody = req("DELETE", f"https://services.leadconnectorhq.com/users/{u['id']}")
        print(" DELETE", dcode, str(dbody)[:180] if not isinstance(dbody, dict) else list(dbody.keys())[:6])

    users = list_users()
    summary = []
    for u in users:
        roles = u.get("roles") or {}
        summary.append(
            {
                "id": u.get("id"),
                "name": u.get("name"),
                "email": u.get("email"),
                "role": roles.get("role"),
                "type": roles.get("type"),
            }
        )
        print("KEEP", u.get("name"), u.get("email"), roles.get("role"), u.get("id"))

    OUT.write_text(
        json.dumps({"results": results, "users": summary}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("saved")


if __name__ == "__main__":
    main()
