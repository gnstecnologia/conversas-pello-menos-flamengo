# -*- coding: utf-8 -*-
import json
import urllib.error
import urllib.request
from pathlib import Path

ENV = Path(r"c:\Users\GC1\Desktop\Automação GHL\.env")
vals = {}
for line in ENV.read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()

KEY = vals["GHL_GAMMA_API_KEY"]
LOC = vals["GHL_GAMMA_LOCATION_ID"]
COMPANY = "PIK3OmRl8Y7U0cy1tHSR"

PERMS = {
    "campaignsEnabled": False,
    "campaignsReadOnly": False,
    "contactsEnabled": True,
    "workflowsEnabled": False,
    "workflowsReadOnly": False,
    "triggersEnabled": False,
    "funnelsEnabled": False,
    "websitesEnabled": False,
    "opportunitiesEnabled": True,
    "dashboardStatsEnabled": True,
    "bulkRequestsEnabled": False,
    "appointmentsEnabled": True,
    "reviewsEnabled": False,
    "onlineListingsEnabled": False,
    "phoneCallEnabled": True,
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
    "botService": True,
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
            return resp.status, json.loads(resp.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = raw
        return e.code, parsed


uid = "LxQOtMzWVhRqNLlWnLCI"
code, u = req("GET", f"https://services.leadconnectorhq.com/users/{uid}")
print("GET", code, "role", (u.get("roles") or {}).get("role"), "keys", list(u.keys())[:20] if isinstance(u, dict) else type(u))

tries = [
    {"role": "user", "type": "account", "locationIds": [LOC], "companyId": COMPANY, "permissions": PERMS},
    {"firstName": "Marcello", "lastName": "Comodo", "role": "user", "type": "account", "locationIds": [LOC], "permissions": PERMS},
]
for i, body in enumerate(tries, 1):
    c, b = req("PUT", f"https://services.leadconnectorhq.com/users/{uid}", body)
    roles = b.get("roles") if isinstance(b, dict) else None
    print("try", i, c, roles)

code2, u2 = req("GET", f"https://services.leadconnectorhq.com/users/{uid}")
print("GET after", (u2.get("roles") if isinstance(u2, dict) else u2))
on = [k for k, v in (u2.get("permissions") or {}).items() if v] if isinstance(u2, dict) else []
print("perms on", on)
