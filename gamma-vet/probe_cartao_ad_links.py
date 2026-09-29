# -*- coding: utf-8 -*-
import json
import re
import urllib.request
import urllib.error
from collections import Counter, defaultdict
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

ADS = {
    "120248618435700523": "120248618435710523",
    "120245782879890523": "120245782879900523",
    "120244183810290523": "120244183810310523",
    "120244179908230523": "120244179908220523",
    "120253509877330523": "120253509877310523",
    "120253508815200523": "120253508815200523",
    "120253510024870523": "120253510024860523",
}


def req(url):
    r = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Authorization": f"Bearer {KEY}",
            "Version": "2021-04-15",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
        },
    )
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        return {"_err": e.code, "_body": e.read().decode("utf-8", errors="replace")}


RX_URL = re.compile(r"Source URL:\s*(https?://\S+)", re.I)
RX_ID = re.compile(r"Source ID:\s*([0-9]+)", re.I)
RX_TITLE = re.compile(r"(?:Title|Headline):\s*(.+)", re.I)

by_ad = {ad: {"urls": Counter(), "titles": Counter(), "hits": 0} for ad in ADS}
other_ads = Counter()
convs_checked = 0
start_after = None
pages = 0

while pages < 50:
    pages += 1
    url = (
        f"https://services.leadconnectorhq.com/conversations/search"
        f"?locationId={LOC}&limit=20&sort=desc&sortBy=last_message_date"
    )
    if start_after:
        url += f"&startAfterDate={start_after}"
    data = req(url)
    convs = data.get("conversations") or []
    if not convs:
        print("empty page", pages)
        break
    for c in convs:
        cid = c.get("id")
        last_date = c.get("lastMessageDate") or c.get("dateUpdated")
        if last_date:
            start_after = last_date
        if not cid:
            continue
        convs_checked += 1
        msgs = req(f"https://services.leadconnectorhq.com/conversations/{cid}/messages")
        messages = msgs.get("messages") or msgs.get("data") or []
        if isinstance(messages, dict):
            messages = messages.get("messages") or messages.get("data") or []
        if not isinstance(messages, list):
            continue
        # look at earliest messages first (ad payload is usually first inbound)
        for m in messages:
            body = str(m.get("body") or m.get("message") or "")
            if "Source ID" not in body and "Source URL" not in body:
                continue
            mid = RX_ID.search(body)
            urls = [u.rstrip(").,") for u in RX_URL.findall(body)]
            title = RX_TITLE.search(body)
            ad = mid.group(1) if mid else None
            if ad in by_ad:
                by_ad[ad]["hits"] += 1
                for u in urls:
                    by_ad[ad]["urls"][u] += 1
                if title:
                    by_ad[ad]["titles"][title.group(1).strip()[:140]] += 1
            elif ad:
                other_ads[ad] += 1
    filled = sum(1 for v in by_ad.values() if v["urls"])
    print("page", pages, "convs", convs_checked, "filled", filled, "/", len(by_ad))
    if filled == len(by_ad) and all(v["hits"] >= 3 for v in by_ad.values()):
        break

out = {}
for ad, camp in ADS.items():
    info = by_ad[ad]
    out[ad] = {
        "campaign": camp,
        "ad": ad,
        "hits": info["hits"],
        "urls": info["urls"].most_common(),
        "titles": info["titles"].most_common(3),
    }

payload = {
    "pages": pages,
    "convs_checked": convs_checked,
    "ads": out,
    "other_ads_top": other_ads.most_common(15),
}
(OUT / "cartao-ad-links.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print("saved")
