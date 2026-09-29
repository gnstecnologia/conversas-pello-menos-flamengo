# -*- coding: utf-8 -*-
"""Cria usuarios BOT/HUT com os e-mails pedidos pela cliente e realoca leads.

A API GHL ignora PUT de e-mail no mesmo ID. Por isso:
1) cria Unidade com e-mails de treinamento
2) realoca contatos + oportunidades
3) apaga Unidade antiga (libera bot@ e hut@)
4) cria Gerencia com bot@ / hut@
5) troca followers
6) apaga Gerencia antiga (ohana*)
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ENV = Path(r"c:\Users\GC1\Desktop\Automação GHL\.env")
OUT = Path(r"c:\Users\GC1\Desktop\Automação GHL\pello-menos\bot-hut-email-swap.json")
vals = {}
for line in ENV.read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()

KEY = vals["GHL_PELLO_API_KEY"]
LOC = vals["GHL_PELLO_LOCATION_ID"]
COMPANY = vals.get("GHL_AGENCY_COMPANY_ID", "PIK3OmRl8Y7U0cy1tHSR")
PASSWORD = "@Genesis12345"

OLD_BOT_U = "jWobCJgSOEtPWXxpgYQs"
OLD_BOT_G = "vCwwCVt0G5VflC2NXMuw"
OLD_HUT_U = "IF200gSv1xy4sujLGLbS"
OLD_HUT_G = "1JfqOOJBGpo61YvFuT4r"


def req(method, url, body=None, retries=5):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {KEY}",
        "Version": "2021-07-28",
        "Accept": "application/json",
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": "Mozilla/5.0",
        "Location-Id": LOC,
    }
    last = None
    for i in range(retries):
        r = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(r, timeout=60) as resp:
                raw = resp.read().decode("utf-8")
                return resp.status, json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(raw)
            except Exception:
                parsed = {"_raw": raw[:500]}
            if e.code in (429, 502, 503) and i < retries - 1:
                time.sleep(1.2 * (i + 1))
                continue
            return e.code, parsed
        except Exception as ex:
            last = ex
            time.sleep(0.8 * (i + 1))
    return 0, {"error": str(last)}


def get_user(uid):
    st, d = req("GET", f"https://services.leadconnectorhq.com/users/{uid}")
    u = d.get("user") or d if isinstance(d, dict) else {}
    return st, u if isinstance(u, dict) else {}


def list_users():
    st, d = req("GET", f"https://services.leadconnectorhq.com/users/?locationId={LOC}")
    return st, d.get("users") or [] if isinstance(d, dict) else []


def find_email(users, email):
    email = email.lower()
    return next((u for u in users if (u.get("email") or "").lower() == email), None)


def create_user(first, last, email, template):
    perms = dict(template.get("permissions") or {})
    perms["assignedDataOnly"] = True
    body = {
        "companyId": COMPANY,
        "firstName": first,
        "lastName": last,
        "email": email,
        "password": PASSWORD,
        "type": "account",
        "role": "user",
        "locationIds": [LOC],
        "permissions": perms,
    }
    st, d = req("POST", "https://services.leadconnectorhq.com/users/", body)
    uid = None
    if isinstance(d, dict):
        uid = d.get("id") or (d.get("user") or {}).get("id")
    print(f" CREATE {email} http={st} id={uid} msg={str(d.get('message') if isinstance(d, dict) else d)[:180]}")
    if uid:
        # reforca visao so do atribuido
        put = {
            "companyId": COMPANY,
            "firstName": first,
            "lastName": last,
            "type": "account",
            "role": "user",
            "locationIds": [LOC],
            "permissions": perms,
        }
        if template.get("scopesAssignedToOnly"):
            put["scopesAssignedToOnly"] = template["scopesAssignedToOnly"]
        st2, d2 = req("PUT", f"https://services.leadconnectorhq.com/users/{uid}", put)
        print(f"  PUT perms http={st2}")
    return uid, st, d


def search_contacts(filters, pages=20):
    out = []
    total = None
    for page in range(1, pages + 1):
        st, d = req(
            "POST",
            "https://services.leadconnectorhq.com/contacts/search",
            {"locationId": LOC, "pageLimit": 100, "page": page, "filters": filters},
        )
        if st != 200:
            print(" search contacts err", st, str(d)[:200])
            break
        batch = d.get("contacts") or []
        if total is None:
            total = d.get("total")
        out.extend(batch)
        if not batch or (total is not None and len(out) >= total):
            break
    by = {c["id"]: c for c in out if c.get("id")}
    return total, list(by.values())


def follower_ids(contact):
    ids = []
    for f in contact.get("followers") or []:
        if isinstance(f, str):
            ids.append(f)
        elif isinstance(f, dict):
            ids.append(f.get("id") or f.get("userId") or "")
    return [x for x in ids if x]


def move_contact(cid, old_owner, new_owner, old_follow, new_follow, contact):
    actions = []
    owner = contact.get("assignedTo")
    follows = follower_ids(contact)
    if owner == old_owner or owner != new_owner:
        st, d = req("PUT", f"https://services.leadconnectorhq.com/contacts/{cid}", {"assignedTo": new_owner})
        if st not in (200, 201):
            return "error", {"id": cid, "step": "owner", "code": st, "body": d}
        actions.append("owner")
    if new_follow not in follows:
        st, d = req(
            "POST",
            f"https://services.leadconnectorhq.com/contacts/{cid}/followers",
            {"followers": [new_follow]},
        )
        if st not in (200, 201):
            return "error", {"id": cid, "step": "add_follow", "code": st, "body": d}
        actions.append("add_follow")
    if old_follow in follows and old_follow != new_follow:
        st, d = req(
            "DELETE",
            f"https://services.leadconnectorhq.com/contacts/{cid}/followers",
            {"followers": [old_follow]},
        )
        if st not in (200, 201, 204):
            # tenta ids
            st2, d2 = req(
                "DELETE",
                f"https://services.leadconnectorhq.com/contacts/{cid}/followers",
                {"ids": [old_follow]},
            )
            if st2 not in (200, 201, 204):
                return "error", {"id": cid, "step": "del_follow", "code": st, "body": d, "alt": d2}
        actions.append("del_follow")
    return "ok", {"id": cid, "actions": actions}


def search_opps(assigned_to):
    out = []
    start = None
    for _ in range(30):
        q = f"location_id={LOC}&assigned_to={assigned_to}&limit=100"
        if start:
            q += f"&startAfterId={start}"
        st, d = req("GET", f"https://services.leadconnectorhq.com/opportunities/search?{q}")
        if st != 200:
            print(" opp search err", st, str(d)[:200])
            break
        batch = d.get("opportunities") or []
        out.extend(batch)
        if len(batch) < 100:
            break
        start = batch[-1].get("id")
        if not start:
            break
    by = {o["id"]: o for o in out if o.get("id")}
    return list(by.values())


def move_opp(oid, new_owner, old_follow, new_follow, opp):
    actions = []
    st, d = req(
        "PUT",
        f"https://services.leadconnectorhq.com/opportunities/{oid}",
        {"assignedTo": new_owner},
    )
    if st not in (200, 201):
        return "error", {"id": oid, "step": "owner", "code": st, "body": d}
    actions.append("owner")
    st, d = req(
        "POST",
        f"https://services.leadconnectorhq.com/opportunities/{oid}/followers",
        {"followers": [new_follow]},
    )
    if st in (200, 201):
        actions.append("add_follow")
    if old_follow:
        st, d = req(
            "DELETE",
            f"https://services.leadconnectorhq.com/opportunities/{oid}/followers",
            {"followers": [old_follow]},
        )
        if st in (200, 201, 204):
            actions.append("del_follow")
    return "ok", {"id": oid, "actions": actions, "http_follow_add": True}


def run_pool(items, fn, label):
    stats = {"ok": 0, "error": 0}
    errors = []
    if not items:
        print(f" {label}: 0")
        return stats, errors
    done = 0
    with ThreadPoolExecutor(max_workers=5) as ex:
        futs = [ex.submit(fn, x) for x in items]
        for fut in as_completed(futs):
            kind, info = fut.result()
            done += 1
            stats[kind] = stats.get(kind, 0) + 1
            if kind == "error":
                errors.append(info)
            if done % 40 == 0 or done == len(items):
                print(f"  {label} {done}/{len(items)} {stats}")
    return stats, errors


def main():
    report = {"steps": []}
    st, users = list_users()
    print("users", st, len(users))

    st, bot_u = get_user(OLD_BOT_U)
    st, hut_u = get_user(OLD_HUT_U)
    st, bot_g = get_user(OLD_BOT_G)
    st, hut_g = get_user(OLD_HUT_G)
    print("templates", bot_u.get("email"), hut_u.get("email"), bot_g.get("email"), hut_g.get("email"))

    # --- 1. criar unidades novas (e-mails livres) ---
    wanted_u = [
        ("Unidade Botafogo", "Pello Menos", "Treinamentobot2025@gmail.com", bot_u, "BOT_U"),
        ("Unidade Humaitá", "Pello Menos", "huttreinamento2026@gmail.com", hut_u, "HUT_U"),
    ]
    new_ids = {}
    _, users = list_users()
    for first, last, email, tmpl, key in wanted_u:
        hit = find_email(users, email)
        if hit:
            print("EXISTS", email, hit.get("id"))
            new_ids[key] = hit["id"]
            continue
        uid, http, _ = create_user(first, last, email, tmpl)
        if not uid:
            report["steps"].append({"create": email, "ok": False, "http": http})
            OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            print("ABORT create", email)
            return
        new_ids[key] = uid
        report["steps"].append({"create": email, "ok": True, "id": uid})

    NEW_BOT_U = new_ids["BOT_U"]
    NEW_HUT_U = new_ids["HUT_U"]
    print("NEW_BOT_U", NEW_BOT_U, "NEW_HUT_U", NEW_HUT_U)

    # --- 2. realocar contatos das unidades antigas ---
    # Por enquanto gerencia nova ainda nao existe: so troca owner.
    # Followers da gerencia antiga ficam ate o passo 5.

    def move_owners_only(cid, old_owner, new_owner, contact):
        if contact.get("assignedTo") == new_owner:
            return "ok", {"id": cid, "actions": ["already"]}
        st, d = req("PUT", f"https://services.leadconnectorhq.com/contacts/{cid}", {"assignedTo": new_owner})
        if st not in (200, 201):
            return "error", {"id": cid, "code": st, "body": d}
        return "ok", {"id": cid, "actions": ["owner"]}

    for label, old, new in [("BOT contacts", OLD_BOT_U, NEW_BOT_U), ("HUT contacts", OLD_HUT_U, NEW_HUT_U)]:
        total, cs = search_contacts([{"field": "assignedTo", "operator": "eq", "value": old}])
        print(f"{label} total={total} listed={len(cs)}")
        stats, errors = run_pool(
            cs, lambda c, o=old, n=new: move_owners_only(c["id"], o, n, c), label
        )
        report["steps"].append({"move_contacts": label, "stats": stats, "errors": errors[:20], "n": len(cs)})

    for label, old, new in [("BOT opps", OLD_BOT_U, NEW_BOT_U), ("HUT opps", OLD_HUT_U, NEW_HUT_U)]:
        opps = search_opps(old)
        print(f"{label} n={len(opps)}")

        def fn(o, n=new):
            st, d = req(
                "PUT",
                f"https://services.leadconnectorhq.com/opportunities/{o['id']}",
                {"assignedTo": n},
            )
            if st not in (200, 201):
                return "error", {"id": o["id"], "code": st, "body": d}
            return "ok", {"id": o["id"]}

        stats, errors = run_pool(opps, fn, label)
        report["steps"].append({"move_opps": label, "stats": stats, "errors": errors[:20], "n": len(opps)})

    # verifica se ainda resta assigned na unidade antiga
    for old, name in [(OLD_BOT_U, "old BOT_U"), (OLD_HUT_U, "old HUT_U")]:
        t, cs = search_contacts([{"field": "assignedTo", "operator": "eq", "value": old}])
        print("remaining", name, t)
        report["steps"].append({"remaining_assigned": name, "total": t})
        if t:
            print("ABORT delete, still assigned", name)
            OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            return

    # --- 3. apagar unidades antigas para liberar bot@ / hut@ ---
    for uid, email in [(OLD_BOT_U, "bot@pellomenos.com.br"), (OLD_HUT_U, "hut@pellomenos.com.br")]:
        st, d = req("DELETE", f"https://services.leadconnectorhq.com/users/{uid}")
        print("DELETE unidade", email, uid, st, str(d)[:180])
        report["steps"].append({"delete": email, "id": uid, "http": st, "body": d if st not in (200, 201, 204) else "ok"})
        if st not in (200, 201, 204):
            print("ABORT delete unidade")
            OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            return
        time.sleep(0.5)

    # --- 4. criar gerencias com bot@ / hut@ ---
    wanted_g = [
        ("Gerência Botafogo", "Pello Menos", "bot@pellomenos.com.br", bot_g, "BOT_G"),
        ("Gerência Humaitá", "Pello Menos", "hut@pellomenos.com.br", hut_g, "HUT_G"),
    ]
    _, users = list_users()
    for first, last, email, tmpl, key in wanted_g:
        hit = find_email(users, email)
        if hit:
            print("EXISTS", email, hit.get("id"))
            new_ids[key] = hit["id"]
            continue
        uid, http, _ = create_user(first, last, email, tmpl)
        if not uid:
            report["steps"].append({"create": email, "ok": False, "http": http})
            OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            print("ABORT create gerencia", email)
            return
        new_ids[key] = uid
        report["steps"].append({"create": email, "ok": True, "id": uid})

    NEW_BOT_G = new_ids["BOT_G"]
    NEW_HUT_G = new_ids["HUT_G"]
    print("NEW_BOT_G", NEW_BOT_G, "NEW_HUT_G", NEW_HUT_G)

    def swap_follow_only(cid, old_follow, new_follow, contact):
        follows = follower_ids(contact)
        actions = []
        if new_follow not in follows:
            st, d = req(
                "POST",
                f"https://services.leadconnectorhq.com/contacts/{cid}/followers",
                {"followers": [new_follow]},
            )
            if st not in (200, 201):
                return "error", {"id": cid, "step": "add_follow", "code": st, "body": d}
            actions.append("add_follow")
        if old_follow in follows and old_follow != new_follow:
            st, d = req(
                "DELETE",
                f"https://services.leadconnectorhq.com/contacts/{cid}/followers",
                {"followers": [old_follow]},
            )
            if st not in (200, 201, 204):
                st2, d2 = req(
                    "DELETE",
                    f"https://services.leadconnectorhq.com/contacts/{cid}/followers",
                    {"ids": [old_follow]},
                )
                if st2 not in (200, 201, 204):
                    return "error", {"id": cid, "step": "del_follow", "code": st, "body": d, "alt": d2}
            actions.append("del_follow")
        return "ok", {"id": cid, "actions": actions or ["already"]}

    # --- 5. followers: tira ohana, poe gerencia nova ---
    for label, owner, old_f, new_f in [
        ("BOT follow", NEW_BOT_U, OLD_BOT_G, NEW_BOT_G),
        ("HUT follow", NEW_HUT_U, OLD_HUT_G, NEW_HUT_G),
    ]:
        t, cs = search_contacts([{"field": "assignedTo", "operator": "eq", "value": owner}])
        print(f"{label} contacts {t}")
        stats, errors = run_pool(
            cs,
            lambda c, o=old_f, n=new_f: swap_follow_only(c["id"], o, n, c),
            label,
        )
        report["steps"].append({"followers": label, "stats": stats, "errors": errors[:20]})

        opps = search_opps(owner)
        print(f"{label} opps {len(opps)}")
        stats, errors = run_pool(
            opps, lambda o, of=old_f, nf=new_f, ow=owner: move_opp(o["id"], ow, of, nf, o), label + " opps"
        )
        report["steps"].append({"opp_followers": label, "stats": stats, "errors": errors[:20]})

    # --- 6. apagar gerencia antiga ohana ---
    for uid, email in [(OLD_BOT_G, "ohanabot24@gmail.com"), (OLD_HUT_G, "ohanahut24@gmail.com")]:
        st, d = req("DELETE", f"https://services.leadconnectorhq.com/users/{uid}")
        print("DELETE gerencia", email, uid, st, str(d)[:180])
        report["steps"].append({"delete": email, "id": uid, "http": st})

    _, users = list_users()
    final = []
    for u in users:
        em = (u.get("email") or "").lower()
        if any(x in em for x in ("bot@", "hut@", "treinamento", "ohana")):
            final.append({"id": u.get("id"), "name": u.get("name"), "email": u.get("email")})
    print("FINAL MATCH")
    for row in final:
        print(" ", row)
    report["new_ids"] = new_ids
    report["final"] = final
    report["workflow_replace"] = {
        "BOTAFOGO_assign_owner": {"old": OLD_BOT_U, "new": NEW_BOT_U},
        "BOTAFOGO_gerencia_follower": {"old": OLD_BOT_G, "new": NEW_BOT_G},
        "HUMAITA_assign_owner": {"old": OLD_HUT_U, "new": NEW_HUT_U},
        "HUMAITA_gerencia_follower": {"old": OLD_HUT_G, "new": NEW_HUT_G},
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("saved", OUT)


if __name__ == "__main__":
    main()
