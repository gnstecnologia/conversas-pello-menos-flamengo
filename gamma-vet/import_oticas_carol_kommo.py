# -*- coding: utf-8 -*-
"""Limpa Oticas Carol e importa CSV Kommo (contatos)."""
from __future__ import annotations

import csv
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ENV = Path(r"c:\Users\GC1\Desktop\Automação GHL\.env")
CSV = Path(
    r"C:\Users\GC1\.cursor\projects\c-Users-GC1-Desktop-Automa-o-GHL\attachments"
    r"\7db75c62-1935-4250-968a-5d7b89de1e11\kommo_export_leads_2026-09-18_2.csv"
)
OUT = Path(r"c:\Users\GC1\Desktop\Automação GHL\gamma-vet\oticas-carol-import-result.json")

vals = {}
for line in ENV.read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()

KEY = vals["GHL_OTICAS_CAROL_API_KEY"]
LOC = vals["GHL_OTICAS_CAROL_LOCATION_ID"]


def req(method, url, body=None, retries=3):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {KEY}",
        "Version": "2021-07-28",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0",
    }
    if body is not None:
        headers["Content-Type"] = "application/json; charset=utf-8"
    last_err = None
    for attempt in range(retries):
        r = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(r, timeout=60) as resp:
                raw = resp.read().decode("utf-8")
                return resp.status, json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", errors="replace")
            try:
                return e.code, json.loads(raw)
            except Exception:
                return e.code, raw
        except Exception as e:
            last_err = e
            time.sleep(1.5 * (attempt + 1))
    return 0, {"error": str(last_err)}


def contact_total():
    st, d = req(
        "POST",
        "https://services.leadconnectorhq.com/contacts/search",
        {"locationId": LOC, "pageLimit": 1},
    )
    if st != 200:
        print("total fail", st, d)
        return -1
    return int(d.get("total") or 0)


def fetch_page():
    st, d = req(
        "POST",
        "https://services.leadconnectorhq.com/contacts/search",
        {"locationId": LOC, "page": 1, "pageLimit": 100},
    )
    if st != 200:
        return []
    return d.get("contacts") or []


def wipe_all():
    deleted = 0
    for pass_n in range(1, 30):
        total = contact_total()
        print(f"wipe pass {pass_n} total={total}", flush=True)
        if total <= 0:
            return deleted
        batch = fetch_page()
        if not batch:
            time.sleep(1)
            if contact_total() <= 0:
                return deleted
            continue
        for c in batch:
            cid = c.get("id")
            st, _ = req("DELETE", f"https://services.leadconnectorhq.com/contacts/{cid}")
            if st in (200, 201, 204):
                deleted += 1
            time.sleep(0.05)
        print(f"  deleted so far {deleted}", flush=True)
    return deleted


PHONE_KEYS = (
    "Celular",
    "Telefone comercial",
    "Tel. direto com.",
    "Telefone residencial",
    "Outro telefone",
)
EMAIL_KEYS = ("Email comercial", "Email pessoal", "Outro email")


def clean_phone(v: str) -> str:
    v = (v or "").strip().strip("'").strip()
    if not v or v in ("-", "null", "None"):
        return ""
    return v


def parse_csv():
    with CSV.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    print("csv rows", len(rows), flush=True)
    parsed = []
    seen = set()
    for row in rows:
        name = (row.get("Nome completo") or "").strip()
        phone = ""
        for k in PHONE_KEYS:
            phone = clean_phone(row.get(k) or "")
            if phone:
                break
        email = ""
        for k in EMAIL_KEYS:
            email = (row.get(k) or "").strip()
            if email:
                break
        if not phone and not email:
            continue
        key = phone or email.lower()
        if key in seen:
            continue
        seen.add(key)
        if name.startswith("Lead #"):
            name = ""
        parts = name.split(None, 1) if name else []
        first = parts[0] if parts else "Lead"
        last = parts[1] if len(parts) > 1 else ""
        tags = ["import-kommo"]
        stage = (row.get("Etapa do lead") or "").strip()
        if stage:
            tags.append(("etapa:" + stage)[:50])
        parsed.append(
            {
                "firstName": first,
                "lastName": last,
                "phone": phone or None,
                "email": email or None,
                "tags": tags,
                "source": "kommo-export-2026-09-18",
            }
        )
    print("unique", len(parsed), flush=True)
    return parsed


def create_contact(body):
    payload = {"locationId": LOC}
    for k, v in body.items():
        if v not in (None, "", []):
            payload[k] = v
    st, d = req("POST", "https://services.leadconnectorhq.com/contacts/", payload)
    if st in (200, 201):
        return True, (d.get("contact") or d).get("id"), None
    msg = json.dumps(d, ensure_ascii=False) if not isinstance(d, str) else d
    return False, None, f"{st} {msg[:250]}"


def main():
    st, d = req("GET", f"https://services.leadconnectorhq.com/locations/{LOC}")
    print("LOC", (d.get("location") or d).get("name"), flush=True)
    wiped = wipe_all()
    print("wiped", wiped, "final total", contact_total(), flush=True)

    rows = parse_csv()
    created = failed = 0
    errors = []
    for i, row in enumerate(rows, 1):
        ok, cid, err = create_contact(row)
        if ok:
            created += 1
        else:
            failed += 1
            if len(errors) < 40:
                errors.append({"i": i, "phone": row.get("phone"), "err": err})
            if "429" in (err or "") or i <= 3:
                print("fail", i, err, flush=True)
                time.sleep(1)
        if i % 100 == 0:
            print(f"import {i}/{len(rows)} created={created} fail={failed}", flush=True)
        time.sleep(0.08)

    summary = {
        "wiped": wiped,
        "csv_unique": len(rows),
        "created": created,
        "failed": failed,
        "final_total": contact_total(),
        "errors_sample": errors,
    }
    OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("SUMMARY", json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
