# -*- coding: utf-8 -*-
"""Atribui contatos disparo 21/08: Unidade SJC = owner, Gerencia SJC = follower."""
from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ENV = Path(r"c:\Users\GC1\Desktop\Automação GHL\.env")
OUT = Path(r"c:\Users\GC1\Desktop\Automação GHL\pello-menos\pello-sjc-assign-report.json")
LOG = Path(r"c:\Users\GC1\Desktop\Automação GHL\pello-menos\pello-sjc-assign.log")

TAG = "disparo 21/08"
OWNER_ID = "xHPu5HbnVNPF6QuPnf73"  # Unidade São José dos Campos
FOLLOWER_ID = "f7YzBTlfq3LJXu4KIVg7"  # Gerência São José dos Campos
WORKERS = 6

vals = {}
for line in ENV.read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()

KEY = vals["GHL_PELLO_API_KEY"]
LOC = vals["GHL_PELLO_LOCATION_ID"]
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


def follower_ids(contact):
    ids = []
    for f in contact.get("followers") or []:
        if isinstance(f, str):
            ids.append(f)
        elif isinstance(f, dict):
            ids.append(f.get("id") or f.get("userId") or "")
    return [x for x in ids if x]


def list_tagged():
    contacts = []
    page = 1
    total = None
    while page <= 80:
        body = {
            "locationId": LOC,
            "pageLimit": 100,
            "page": page,
            "filters": [{"field": "tags", "operator": "eq", "value": TAG}],
        }
        code, data = req("POST", "https://services.leadconnectorhq.com/contacts/search", body)
        if code != 200:
            log(f"search page {page} err {code} {data}")
            break
        if total is None:
            total = data.get("total")
            log(f"search total {total}")
        batch = data.get("contacts") or []
        if not batch:
            break
        contacts.extend(batch)
        log(f"listed {len(contacts)}/{total}")
        if total is not None and len(contacts) >= total:
            break
        page += 1
        time.sleep(0.05)
    # unique
    by_id = {}
    for c in contacts:
        if c.get("id"):
            by_id[c["id"]] = c
    return list(by_id.values())


def assign_one(cid, contact=None):
    contact = contact or {}
    already_owner = (contact.get("assignedTo") or "") == OWNER_ID
    already_follow = FOLLOWER_ID in follower_ids(contact)
    actions = []
    if not already_owner:
        code, body = req("PUT", f"https://services.leadconnectorhq.com/contacts/{cid}", {"assignedTo": OWNER_ID})
        if code not in (200, 201):
            return "error", {"id": cid, "step": "owner", "code": code, "body": body}
        actions.append("owner")
    else:
        actions.append("owner_ok")
    if not already_follow:
        code, body = req(
            "POST",
            f"https://services.leadconnectorhq.com/contacts/{cid}/followers",
            {"followers": [FOLLOWER_ID]},
        )
        if code not in (200, 201):
            return "error", {"id": cid, "step": "follower", "code": code, "body": body}
        actions.append("follower")
    else:
        actions.append("follower_ok")
    kind = "ok" if actions == ["owner_ok", "follower_ok"] else "updated"
    return kind, {"id": cid, "actions": actions}


def main():
    LOG.write_text("", encoding="utf-8")
    contacts = list_tagged()
    log(f"unique contacts {len(contacts)}")
    stats = {"updated": 0, "ok": 0, "error": 0}
    errors = []
    done = 0
    total = len(contacts)

    def work(c):
        return assign_one(c["id"], c)

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = [ex.submit(work, c) for c in contacts]
        for fut in as_completed(futs):
            kind, info = fut.result()
            done += 1
            stats[kind] = stats.get(kind, 0) + 1
            if kind == "error":
                errors.append(info)
            if done % 50 == 0 or done == total:
                log(f"progress {done}/{total} {stats}")
    report = {"owner": OWNER_ID, "follower": FOLLOWER_ID, "tag": TAG, "total": total, "stats": stats, "errors": errors[:200]}
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"DONE {stats} errors={len(errors)} report={OUT}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--probe":
        LOG.write_text("", encoding="utf-8")
        contacts = list_tagged()
        print("n", len(contacts))
        sample = contacts[:2]
        for c in sample:
            print("before", c.get("id"), c.get("email"), "assigned", c.get("assignedTo"), "followers", c.get("followers"))
            print("assign", assign_one(c["id"], c))
            code, body = req("GET", f"https://services.leadconnectorhq.com/contacts/{c['id']}")
            after = (body or {}).get("contact") or body
            print("after assigned", after.get("assignedTo"), "followers", after.get("followers"))
    else:
        main()
