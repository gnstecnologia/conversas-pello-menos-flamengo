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

OFF_EXTRAS = {
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

IDS = [
    "LxQOtMzWVhRqNLlWnLCI",
    "Daia1y3n2C1F1VfXIdvV",
    "2XSRsWDCgmL11WFIerwr",
    "NZhcmQNt4ubbz5YruDU9",
    "XXh1AeDBl3URNuqBZgiZ",
    "N6PlrM7lGh6ej4R869sH",
    "kSZcuwcDWLcaEfX9BwEC",
]


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


for uid in IDS:
    code, u = req("GET", f"https://services.leadconnectorhq.com/users/{uid}")
    perms = dict(u.get("permissions") or {})
    perms.update(OFF_EXTRAS)
    perms.update(KEEP_ON)
    body = {
        "firstName": u.get("firstName") or "",
        "lastName": u.get("lastName") or "",
        "role": "user",
        "type": "account",
        "locationIds": [LOC],
        "companyId": COMPANY,
        "permissions": perms,
    }
    c, b = req("PUT", f"https://services.leadconnectorhq.com/users/{uid}", body)
    on = sorted([k for k, v in (b.get("permissions") or {}).items() if v]) if isinstance(b, dict) else []
    print(u.get("email"), c, (b.get("roles") or {}).get("role") if isinstance(b, dict) else str(b)[:120])
    print("  on:", ", ".join(on))
