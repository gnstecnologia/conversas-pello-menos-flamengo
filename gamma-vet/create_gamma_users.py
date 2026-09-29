# -*- coding: utf-8 -*-
"""Cria usuarios Gamma Vet e deixa todos (incl. Marcello) como User com perms restritas."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

ENV = Path(r"c:\Users\GC1\Desktop\Automação GHL\.env")
OUT = Path(r"c:\Users\GC1\Desktop\Automação GHL\gamma-vet\gamma-users-created.json")
vals = {}
for line in ENV.read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()

KEY = vals["GHL_GAMMA_API_KEY"]
LOC = vals["GHL_GAMMA_LOCATION_ID"]
COMPANY = "PIK3OmRl8Y7U0cy1tHSR"
PASSWORD = "@Genesis12345"
MARCELLO_ID = "LxQOtMzWVhRqNLlWnLCI"

NEW_USERS = [
    {"firstName": "Mariana", "lastName": "Gantois", "email": "mariana.gantois@gammavet.com.br"},
    {"firstName": "Gustavo", "lastName": "Cobucci", "email": "gustavo.cobucci@gammavet.com.br"},
    {"firstName": "Marcella", "lastName": "Rosa", "email": "marcella.rosa@gammavet.com.br"},
    {"firstName": "Fernanda", "lastName": "Meirelles", "email": "fernanda.meirelles@gammavet.com.br"},
    {"firstName": "Raquel", "lastName": "Recepcao", "email": "sac@gammavet.com.br"},
    {"firstName": "Yasmin", "lastName": "Recepcao", "email": "agendamento@gammavet.com.br"},
]

# Ligado: conversas, Conversation AI / I.A, calendarios, oportunidades, tags (criar/editar), dashboard.
# Desligado: marketing, funnels, sites, pagamentos, settings, workflows, etc.
PERMS = {
    "campaignsEnabled": False,
    "campaignsReadOnly": False,
    "contactsEnabled": True,  # conversas/CRM básico costuma exigir
    "workflowsEnabled": False,
    "workflowsReadOnly": False,
    "triggersEnabled": False,
    "funnelsEnabled": False,
    "websitesEnabled": False,
    "opportunitiesEnabled": True,
    "dashboardStatsEnabled": True,
    "bulkRequestsEnabled": False,
    "appointmentsEnabled": True,  # calendarios
    "reviewsEnabled": False,
    "onlineListingsEnabled": False,
    "phoneCallEnabled": True,  # conversas
    "conversationsEnabled": True,
    "assignedDataOnly": False,
    "adwordsReportingEnabled": False,
    "membershipEnabled": False,
    "facebookAdsReportingEnabled": False,
    "attributionsReportingEnabled": False,
    "settingsEnabled": False,
    "tagsEnabled": True,
    "leadValueEnabled": False,
    "marketingEnabled": False,
    "agentReportingEnabled": True,
    "botService": True,  # Conversation AI / I.A
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


def create_or_update(u):
    email = u["email"]
    existing = [x for x in list_users() if (x.get("email") or "").lower() == email.lower()]
    body = {
        "firstName": u["firstName"],
        "lastName": u["lastName"],
        "email": email,
        "password": PASSWORD,
        "type": "account",
        "role": "user",
        "locationIds": [LOC],
        "permissions": PERMS,
        "companyId": COMPANY,
    }
    if existing:
        uid = existing[0]["id"]
        print("EXISTS", email, uid, "-> PUT")
        # email update unsupported; omit email on PUT
        put = {k: v for k, v in body.items() if k != "email"}
        c, b = req("PUT", f"https://services.leadconnectorhq.com/users/{uid}", put)
        print(" PUT", c, str(b)[:220] if not isinstance(b, dict) else (b.get("email") or b.get("id") or list(b.keys())[:6]))
        return uid, c, b
    print("CREATE", email)
    c, b = req("POST", "https://services.leadconnectorhq.com/users/", body)
    print(" POST", c, str(b)[:300] if not isinstance(b, dict) else (b.get("email") or b.get("id") or b.get("message") or list(b.keys())[:8]))
    uid = None
    if isinstance(b, dict):
        uid = b.get("id") or (b.get("user") or {}).get("id")
    return uid, c, b


def demote_marcello():
    print("DEMOTE Marcello", MARCELLO_ID)
    c, b = req(
        "PUT",
        f"https://services.leadconnectorhq.com/users/{MARCELLO_ID}",
        {
            "firstName": "Marcello",
            "lastName": "Comodo",
            "type": "account",
            "role": "user",
            "locationIds": [LOC],
            "permissions": PERMS,
            "companyId": COMPANY,
        },
    )
    print(" PUT Marcello", c, (b.get("roles") if isinstance(b, dict) else str(b)[:250]))
    return c, b


def main():
    results = []
    for u in NEW_USERS:
        uid, code, body = create_or_update(u)
        results.append({"email": u["email"], "id": uid, "code": code, "ok": code in (200, 201)})
    demote_marcello()
    users = list_users()
    summary = []
    for x in users:
        roles = x.get("roles") or {}
        perms = x.get("permissions") or {}
        on = [k for k, v in perms.items() if v] if isinstance(perms, dict) else []
        summary.append(
            {
                "id": x.get("id"),
                "name": x.get("name"),
                "email": x.get("email"),
                "role": roles.get("role"),
                "type": roles.get("type"),
                "perms_on": on,
            }
        )
        print(f"{x.get('name')}\t{x.get('email')}\t{roles.get('role')}\t{x.get('id')}")
    OUT.write_text(
        json.dumps({"creates": results, "users": summary}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("saved", OUT)


if __name__ == "__main__":
    main()
