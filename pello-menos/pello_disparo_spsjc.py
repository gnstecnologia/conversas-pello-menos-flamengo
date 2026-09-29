# -*- coding: utf-8 -*-
"""Importa Clientes SPSJC na Pello Menos (Franchising): cria/atualiza, email e tag."""
from __future__ import annotations

import json
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ENV = Path(r"c:\Users\GC1\Desktop\Automação GHL\.env")
SRC = Path(r"c:\Users\GC1\Downloads\Clientes SPSJC.txt")
OUT = Path(r"c:\Users\GC1\Desktop\Automação GHL\pello-menos\pello-disparo-spsjc-report.json")
LOG = Path(r"c:\Users\GC1\Desktop\Automação GHL\pello-menos\pello-disparo-spsjc.log")

TAG = "disparo 21/08"
WORKERS = 6
vals = {}
for line in ENV.read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()

KEY = vals["GHL_PELLO_API_KEY"]
LOC = vals["GHL_PELLO_LOCATION_ID"]
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
CODE_RE = re.compile(r"^(\d{8})\s+(.+)$")
LOCK = threading.Lock()


def log(msg: str) -> None:
    with LOCK:
        print(msg, flush=True)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(msg + "\n")


def req(method, url, body=None):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {KEY}",
        "Version": "2021-07-28",
        "Accept": "application/json",
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": "Mozilla/5.0",
    }
    for i in range(7):
        r = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(r, timeout=60) as resp:
                raw = resp.read().decode("utf-8")
                return resp.status, json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            err = e.read().decode("utf-8", errors="replace")
            if e.code in (429, 502, 503) and i < 6:
                time.sleep(1.5 * (i + 1))
                continue
            try:
                parsed = json.loads(err)
            except Exception:
                parsed = {"raw": err[:500]}
            return e.code, parsed
        except Exception as ex:
            if i < 6:
                time.sleep(1 + i)
                continue
            return 0, {"error": str(ex)}
    return 429, {"error": "rate limited"}


def parse_rows():
    text = SRC.read_bytes().decode("cp1252")
    rows = []
    skipped = []
    for i, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        parts = line.split("\t")
        while len(parts) < 3:
            parts.append("")
        col0, email, phone = parts[0].strip(), parts[1].strip(), parts[2].strip()
        m = CODE_RE.match(col0)
        if m:
            code, name = m.group(1), m.group(2).strip()
        else:
            code, name = "", col0
        email = email.lower().strip()
        phone_digits = re.sub(r"\D", "", phone)
        rec = {
            "line": i,
            "code": code,
            "name": " ".join(name.split()),
            "email": email,
            "phone_raw": phone.strip(),
            "phone": normalize_phone(phone_digits),
        }
        if not rec["email"] or not EMAIL_RE.match(rec["email"]):
            skipped.append(rec)
            continue
        rows.append(rec)
    by_email = {}
    dupes = 0
    for rec in rows:
        prev = by_email.get(rec["email"])
        if prev is None:
            by_email[rec["email"]] = rec
        else:
            dupes += 1
            if rec["phone"] and not prev["phone"]:
                by_email[rec["email"]] = rec
    return list(by_email.values()), skipped, dupes, len(rows)


def normalize_phone(digits: str):
    if not digits:
        return None
    if digits.startswith("55") and len(digits) in (12, 13):
        return "+" + digits
    if len(digits) in (10, 11):
        return "+55" + digits
    return None


def split_name(name: str):
    parts = name.split(" ", 1)
    first = parts[0].title()
    last = parts[1].title() if len(parts) > 1 else ""
    return first, last


def has_tag(contact, tag):
    return tag.lower() in [str(t).lower() for t in (contact.get("tags") or [])]


def ensure_tag():
    code, data = req("GET", f"https://services.leadconnectorhq.com/locations/{LOC}/tags")
    names = {t.get("name") for t in (data or {}).get("tags") or []}
    if TAG in names:
        log(f"tag exists: {TAG}")
        return
    c, body = req("POST", f"https://services.leadconnectorhq.com/locations/{LOC}/tags", {"name": TAG})
    log(f"create tag {TAG} -> {c}")
    if c not in (200, 201):
        log(f"tag create body {body}")


def upsert_one(rec):
    first, last = split_name(rec["name"])
    payload = {
        "locationId": LOC,
        "email": rec["email"],
        "name": rec["name"].title(),
        "firstName": first,
        "lastName": last,
        "source": "Clientes SPSJC",
    }
    if rec["phone"]:
        payload["phone"] = rec["phone"]
    code, body = req("POST", "https://services.leadconnectorhq.com/contacts/upsert", payload)
    if code not in (200, 201):
        return "error", {"email": rec["email"], "step": "upsert", "code": code, "body": body}
    contact = (body or {}).get("contact") or {}
    cid = contact.get("id")
    is_new = bool((body or {}).get("new"))
    if not cid:
        return "error", {"email": rec["email"], "step": "no_id", "body": body}
    actions = ["created" if is_new else "upserted"]
    if rec["email"] and (contact.get("email") or "").lower() != rec["email"]:
        # upsert matched by phone; force email
        c2, b2 = req("PUT", f"https://services.leadconnectorhq.com/contacts/{cid}", {"email": rec["email"]})
        if c2 in (200, 201):
            actions.append("added_email")
        else:
            return "error", {"id": cid, "email": rec["email"], "step": "put_email", "code": c2, "body": b2}
    if not has_tag(contact, TAG):
        c3, b3 = req("POST", f"https://services.leadconnectorhq.com/contacts/{cid}/tags", {"tags": [TAG]})
        if c3 not in (200, 201):
            return "error", {"id": cid, "email": rec["email"], "step": "tag", "code": c3, "body": b3}
        actions.append("tagged")
    else:
        actions.append("already_tagged")
    kind = "created" if is_new else "updated"
    return kind, {"id": cid, "email": rec["email"], "actions": actions}


def main():
    LOG.write_text("", encoding="utf-8")
    rows, skipped, dupes, raw_with_email = parse_rows()
    log(f"location {LOC}")
    log(f"raw_with_email {raw_with_email} unique {len(rows)} dup_emails {dupes} skipped_no_email {len(skipped)}")
    ensure_tag()
    stats = {"created": 0, "updated": 0, "error": 0, "already_ok": 0}
    errors = []
    done = 0
    total = len(rows)

    def work(rec):
        return rec, upsert_one(rec)

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = [ex.submit(work, rec) for rec in rows]
        for fut in as_completed(futs):
            rec, (kind, info) = fut.result()
            done += 1
            if kind == "created":
                stats["created"] += 1
            elif kind == "updated":
                if "already_tagged" in info.get("actions", []) and "added_email" not in info.get("actions", []):
                    stats["already_ok"] += 1
                else:
                    stats["updated"] += 1
            else:
                stats["error"] += 1
                errors.append(info)
            if done % 50 == 0 or done == total:
                log(f"progress {done}/{total} {stats}")
    report = {
        "tag": TAG,
        "locationId": LOC,
        "unique_emails": total,
        "skipped_no_email": [{"name": s["name"], "code": s["code"], "email": s["email"], "phone": s["phone_raw"]} for s in skipped],
        "stats": stats,
        "errors": errors[:300],
        "error_count": len(errors),
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"DONE {stats} errors={len(errors)} report={OUT}")


if __name__ == "__main__":
    main()
