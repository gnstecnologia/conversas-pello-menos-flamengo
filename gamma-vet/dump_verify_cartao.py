# -*- coding: utf-8 -*-
import json
import urllib.request
from pathlib import Path

ENV = Path(r"c:\Users\GC1\Desktop\Automação GHL\.env")
vals = {}
for line in ENV.read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()
KEY = vals["GHL_CARTAO_TODOS_CG_API_KEY"]
LOC = vals["GHL_CARTAO_TODOS_CG_LOCATION_ID"]
OUT = Path(r"c:\Users\GC1\Desktop\Automação GHL\gamma-vet")


def get(url):
    r = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {KEY}",
        "Version": "2021-07-28",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0",
    })
    with urllib.request.urlopen(r, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))

tags = get(f"https://services.leadconnectorhq.com/locations/{LOC}/tags").get("tags") or []
names = [t.get("name") for t in tags]
c = get("https://services.leadconnectorhq.com/contacts/waCVkl7fmISImSQzWXA4").get("contact") or {}
o = get("https://services.leadconnectorhq.com/opportunities/8UiUd27vmxDUXyw4L5vq").get("opportunity") or {}
payload = {
    "location_tags": names,
    "contact_tags": c.get("tags"),
    "contact_cfs": c.get("customFields"),
    "opp_cfs": o.get("customFields"),
}
(OUT / "cartao-agosto-verify.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print("wrote")
