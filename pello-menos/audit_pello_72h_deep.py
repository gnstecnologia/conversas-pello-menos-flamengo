# -*- coding: utf-8 -*-
"""Deep audit: settings 72h, WhatsApp templates, workflows de anúncio, locations Pello."""
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

FK = vals["GHL_PELLO_API_KEY"]
FLOC = vals["GHL_PELLO_LOCATION_ID"]
MK = vals["GHL_PELLO_MODELO_API_KEY"]
MLOC = vals["GHL_PELLO_MODELO_LOCATION_ID"]
ND = vals.get("GHL_NEW_DIGITAL_API_KEY")


def req(key, path, version="2021-07-28", location_id=None):
    headers = {
        "Authorization": f"Bearer {key}",
        "Version": version,
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0",
    }
    if location_id:
        headers["Location-Id"] = location_id
    r = urllib.request.Request("https://services.leadconnectorhq.com" + path, headers=headers)
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"_raw": raw[:400]}
    except Exception as ex:
        return 0, {"_err": str(ex)}


def walk_hits(obj, path=""):
    hits = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}.{k}" if path else k
            kl = k.lower()
            if any(x in kl for x in ("72", "24", "window", "whatsapp", "template", "ctwa", "ads", "facebook", "entry")):
                hits.append((p, v if not isinstance(v, (dict, list)) else type(v).__name__))
            hits.extend(walk_hits(v, p))
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:50]):
            hits.extend(walk_hits(v, f"{path}[{i}]"))
    elif isinstance(obj, str):
        sl = obj.lower()
        if any(x in sl for x in ("72 hour", "72h", "24 hour", "24h", "ctwa", "click to whatsapp", "entry point", "janela")):
            hits.append((path, obj[:200]))
    return hits


print("=== SEARCH LOCATIONS PELLO ===")
for key, label in [(FK, "FRANCHISING_KEY"), (MK, "MODELO_KEY"), (ND, "NEW_DIGITAL")]:
    if not key:
        continue
    st, d = req(key, "/locations/search?limit=100", location_id=FLOC)
    print(label, "search", st)
    locs = d.get("locations") or [] if isinstance(d, dict) else []
    print(" n", len(locs))
    for L in locs:
        n = L.get("name") or ""
        if any(x in n.lower() for x in ("pello", "franq", "modelo")):
            print("  ", L.get("id"), n)

print("\n=== LOCATION SETTINGS FRANCHISING ===")
st, locd = req(FK, f"/locations/{FLOC}")
L = locd.get("location") or locd
settings = L.get("settings") if isinstance(L, dict) else {}
print("settings type", type(settings), "keys", list(settings)[:40] if isinstance(settings, dict) else settings)
if isinstance(settings, dict):
    for k, v in settings.items():
        kl = k.lower()
        if any(x in kl for x in ("whats", "72", "24", "window", "template", "sms", "facebook", "ad", "convers", "saas")):
            print(f"  SET {k}={v!r}"[:300])
hits = walk_hits(L)
print("walk hits", len(hits))
for p, v in hits[:40]:
    print(" ", p, "=", str(v)[:180])

print("\n=== WHATSAPP TEMPLATES type=whatsapp ===")
for key, loc, label in [(FK, FLOC, "FRANCHISING"), (MK, MLOC, "MODELO")]:
    for q in [
        f"/locations/{loc}/templates?deleted=false&skip=0&limit=100&originId={loc}&type=whatsapp",
        f"/locations/{loc}/templates?deleted=false&skip=0&limit=100&originId={loc}",
        f"/locations/{loc}/templates?type=whatsapp&originId={loc}",
    ]:
        st, d = req(key, q, location_id=loc)
        tpls = d.get("templates") if isinstance(d, dict) else None
        n = len(tpls) if isinstance(tpls, list) else d
        print(label, st, q.split("?")[-1][:70], "n=", n if not isinstance(n, dict) else list(n)[:8])
        if isinstance(tpls, list):
            for t in tpls:
                typ = t.get("type")
                name = t.get("name")
                print("   ", typ, "|", name, "|", str(t.get("template"))[:120])

print("\n=== WORKFLOW DETAILS ===")
wf_ids = [
    "121bfe5d-a783-4a8a-b9ab-4652c314f664",
    "dce24b9f-5c4b-4df8-975d-d9b3a9fa444c",
    "d5d49564-0ef0-4b3c-a875-6a7c68ef69fb",
    "f705f489-1980-45a1-bf5c-520270490fe4",
    "e3c6f39d-b104-4f5d-a725-a95fca09ae89",
]
for wid in wf_ids:
    for p in [
        f"/workflows/{wid}",
        f"/workflows/{wid}?locationId={FLOC}",
        f"/funnels/workflow/{wid}",
        f"/workflow/{wid}",
    ]:
        st, d = req(FK, p, location_id=FLOC)
        if st == 404:
            continue
        print("WF", wid[:8], p, st)
        if isinstance(d, dict):
            print(" keys", list(d.keys())[:20])
            h = walk_hits(d)
            for hp, hv in h[:25]:
                print("  HIT", hp, "=", str(hv)[:160])
            # save first successful
            (OUT / f"pello-wf-{wid[:8]}.json").write_text(
                json.dumps(d, ensure_ascii=False, indent=2, default=str)[:200000], encoding="utf-8"
            )
            break
        else:
            print(" ", str(d)[:150])

print("\n=== CONVERSATION CHANNEL / WHATSAPP INTEGRATION ===")
for p in [
    f"/conversations/locations/{FLOC}/channel",
    f"/locations/{FLOC}/conversation-channel",
    "/conversations/channel",
    f"/integrations/whatsapp?locationId={FLOC}",
    f"/whatsapp/accounts?locationId={FLOC}",
    f"/whatsapp/business/profile?locationId={FLOC}",
    f"/conversations/providers/whatsapp?locationId={FLOC}",
    f"/conversations/whatsapp/templates?locationId={FLOC}",
    f"/whatsapp/message-templates?locationId={FLOC}",
    f"/saas/whatsapp?locationId={FLOC}",
]:
    st, d = req(FK, p, location_id=FLOC)
    print(st, p, str(d)[:180].replace("\n", " "))
