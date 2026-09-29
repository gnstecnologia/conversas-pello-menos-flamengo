# -*- coding: utf-8 -*-
"""Troca senha dos 2 usuarios Centro Pello Menos."""
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

KEY = vals["GHL_PELLO_API_KEY"]
PASSWORD = "@Genesis12345"
USERS = [
    ("NqnguRmchSqGQ3WIjuDR", "Gerência Centro", "Cen130123@gmail.com"),
    ("8i0aKNzxG2OQPqOTZJqQ", "Unidade Centro", "cen@pellomenos.com.br"),
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
        return e.code, e.read().decode("utf-8", errors="replace")


for uid, label, email in USERS:
    code, data = req("GET", f"https://services.leadconnectorhq.com/users/{uid}")
    print("GET", label, code)
    u = data.get("user") or data if isinstance(data, dict) else {}
    if not isinstance(u, dict) or not u.get("id"):
        print("  fail get", str(data)[:300])
        continue
    # minimal password update first
    payloads = [
        {"password": PASSWORD},
        {
            "password": PASSWORD,
            "email": u.get("email") or email,
            "firstName": u.get("firstName") or "",
            "lastName": u.get("lastName") or "",
        },
    ]
    for i, body in enumerate(payloads, 1):
        c, b = req("PUT", f"https://services.leadconnectorhq.com/users/{uid}", body)
        print(f"  PUT try{i}", c, str(b)[:250] if not isinstance(b, dict) else list(b.keys())[:8])
        if c in (200, 201):
            print("  OK", label, email)
            break
    else:
        print("  FAILED", label)
