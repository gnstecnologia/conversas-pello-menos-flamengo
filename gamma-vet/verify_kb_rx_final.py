# -*- coding: utf-8 -*-
import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.stdout.reconfigure(encoding="utf-8")
OUT = Path(r"c:\Users\GC1\Desktop\Automação GHL\gamma-vet")
vals = {}
for line in Path(r"c:\Users\GC1\Desktop\Automação GHL\.env").read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()
TOKEN = vals["GHL_GAMMA_API_KEY"]
LOC = vals["GHL_GAMMA_LOCATION_ID"]
KB = vals["GHL_GAMMA_KB_ID"]
CAL = json.loads((OUT / "calendar-ids-live.json").read_text(encoding="utf-8"))
TZ = ZoneInfo("America/Sao_Paulo")
now = datetime.now(TZ).replace(hour=0, minute=0, second=0, microsecond=0)
s = int(now.timestamp() * 1000)
e = int((now + timedelta(days=16)).timestamp() * 1000)


def get(url, ver="2021-07-28"):
    cmd = [
        "curl.exe", "-s", url,
        "-H", f"Authorization: Bearer {TOKEN}",
        "-H", f"Version: {ver}",
        "-H", "Accept: application/json",
        "-H", "User-Agent: Mozilla/5.0",
    ]
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace").stdout


for key in ("rx", "tomo", "fernanda"):
    d = json.loads(
        get(f"https://services.leadconnectorhq.com/calendars/{CAL[key]}/free-slots?startDate={s}&endDate={e}")
    )
    print(key)
    for day in ("2026-09-05", "2026-09-12"):
        slots = (d.get(day) or {}).get("slots") or []
        print(" ", day, "n=", len(slots), "ex=", slots[:2])

raw = get(f"https://services.leadconnectorhq.com/knowledge-base/files?locationId={LOC}&knowledgeBaseId={KB}&limit=10")
files = (json.loads(raw).get("data") or {}).get("files") or []
for f in files:
    print("KB", f.get("name"), f.get("status"), f.get("size"))
print("TXT lines", (OUT / "Procedimentos_GammaVet_KB.txt").read_text(encoding="utf-8").count("\n"))
