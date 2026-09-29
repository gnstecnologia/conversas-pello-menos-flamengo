# -*- coding: utf-8 -*-
"""Audit Pello: janela 72h CTWA + templates em Franchising e Franqueadora."""
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ENV = Path(r"c:\Users\GC1\Desktop\Automação GHL\.env")
OUT = Path(r"c:\Users\GC1\Desktop\Automação GHL\pello-menos")
vals = {}
for line in ENV.read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()

ACCOUNTS = [
    ("PELLO_FRANCHISING", vals["GHL_PELLO_API_KEY"], vals["GHL_PELLO_LOCATION_ID"]),
    ("PELLO_MODELO", vals["GHL_PELLO_MODELO_API_KEY"], vals["GHL_PELLO_MODELO_LOCATION_ID"]),
    ("PELLO_URG", vals["GHL_PELLO_URG_API_KEY"], vals["GHL_PELLO_URG_LOCATION_ID"]),
]


def req(key, method, path, body=None, version="2021-07-28", location_id=None):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {key}",
        "Version": version,
        "Accept": "application/json",
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": "Mozilla/5.0",
    }
    if location_id:
        headers["Location-Id"] = location_id
    r = urllib.request.Request(
        "https://services.leadconnectorhq.com" + path,
        data=data,
        method=method,
        headers=headers,
    )
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"_raw": raw[:500]}
    except Exception as ex:
        return 0, {"_err": str(ex)}


NEEDLES = (
    "72",
    "24",
    "ctwa",
    "click to whatsapp",
    "click-to-whatsapp",
    "facebook page",
    "cta",
    "anuncio",
    "anúncio",
    "ads",
    "ad id",
    "template",
    "entry point",
    "entry-point",
    "janela",
    "window",
    "whatsapp",
)


def blob_hits(obj, extra=""):
    s = (json.dumps(obj, ensure_ascii=False) + " " + extra).lower()
    return [n for n in NEEDLES if n in s]


report = {}

for label, key, loc in ACCOUNTS:
    print("\n" + "=" * 70)
    print(label, loc)
    rec = {"loc": loc, "name": None}

    st, locd = req(key, "GET", f"/locations/{loc}", location_id=loc)
    L = locd.get("location") or locd if isinstance(locd, dict) else {}
    name = L.get("name") if isinstance(L, dict) else None
    rec["name"] = name
    rec["get_loc"] = st
    print("GET loc", st, name)
    if isinstance(L, dict):
        # dump keys that look settings-related
        interesting = {k: L[k] for k in L if any(
            x in k.lower() for x in ("whats", "72", "24", "window", "template", "ad", "facebook", "ctwa", "convers")
        )}
        print(" loc interesting keys", interesting)
        rec["loc_interesting"] = interesting
        rec["loc_keys"] = sorted(L.keys())

    # location with extra
    for p in [
        f"/locations/{loc}?include=settings",
        f"/locations/{loc}/settings",
        f"/whatsapp/templates?locationId={loc}",
        f"/conversations/providers?locationId={loc}",
        f"/conversations/locations/{loc}/settings",
        f"/locations/{loc}/conversationproviders",
        f"/locations/{loc}/whatsapp",
        f"/whatsapp/{loc}",
        f"/whatsapp/phoneNumbers?locationId={loc}",
        f"/conversations/templates?locationId={loc}",
        f"/social-planner/oauth/facebook/accounts?locationId={loc}",
        f"/facebook/{loc}",
        f"/campaigns/?locationId={loc}",
    ]:
        st, d = req(key, "GET", p, location_id=loc)
        hits = blob_hits(d) if isinstance(d, dict) or isinstance(d, list) else []
        print(f" GET {st} {p} hits={hits} type={type(d).__name__} keys={list(d)[:12] if isinstance(d, dict) else ''}")
        rec.setdefault("probes", []).append({"path": p, "st": st, "hits": hits, "preview": str(d)[:240]})

    # workflows
    st, wf = req(key, "GET", f"/workflows/?locationId={loc}", location_id=loc)
    wfs = []
    if isinstance(wf, dict):
        wfs = wf.get("workflows") or wf.get("data") or []
    print("\nWORKFLOWS", st, "n=", len(wfs) if isinstance(wfs, list) else wfs)
    rec["workflows"] = []
    for w in wfs if isinstance(wfs, list) else []:
        wn = w.get("name") or ""
        rec["workflows"].append({"id": w.get("id"), "name": wn, "status": w.get("status"), "hits": blob_hits(w, wn)})
        flag = ""
        low = wn.lower()
        if any(x in low for x in ("whats", "anun", "ads", "ctwa", "72", "template", "facebook", "click", "cta", "janela")):
            flag = " ***"
        print(f"  {w.get('status')} {w.get('id')} | {wn}{flag}")

    # templates snippets
    for p, ver in [
        (f"/locations/{loc}/templates", "2021-07-28"),
        (f"/snapshots/templates?locationId={loc}", "2021-07-28"),
        ("/conversations/messages/mail/templates", "2021-04-15"),
    ]:
        st, d = req(key, "GET", p, version=ver, location_id=loc)
        print(f" TPL {st} {p} {str(d)[:160]}")

    report[label] = rec

(OUT / "pello-72h-probe.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
print("\nWrote pello-72h-probe.json")
