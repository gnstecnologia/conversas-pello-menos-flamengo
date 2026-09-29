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
AGENT = vals["GHL_GAMMA_AGENT_ID"]
CAL = json.loads((OUT / "calendar-ids-live.json").read_text(encoding="utf-8"))
TZ = ZoneInfo("America/Sao_Paulo")


def get(url, ver="2021-07-28"):
    cmd = [
        "curl.exe", "-s", url,
        "-H", f"Authorization: Bearer {TOKEN}",
        "-H", f"Version: {ver}",
        "-H", "Accept: application/json",
        "-H", "User-Agent: Mozilla/5.0",
    ]
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace").stdout


now = datetime.now(TZ).replace(hour=0, minute=0, second=0, microsecond=0)
s = int(now.timestamp() * 1000)
e = int((now + timedelta(days=14)).timestamp() * 1000)
rx_id = CAL["rx"]
rx = json.loads(get(f"https://services.leadconnectorhq.com/calendars/{rx_id}/free-slots?startDate={s}&endDate={e}"))
print("RX sabados:")
for k, v in sorted(rx.items()):
    if k == "traceId" or not isinstance(v, dict):
        continue
    try:
        d = datetime.fromisoformat(k).date()
    except Exception:
        continue
    if d.weekday() == 5:
        slots = v.get("slots") or []
        print(k, "n=", len(slots), "ex=", (slots[:2] if slots else None))

ag = json.loads(get(f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}?locationId={LOC}", "2021-04-15"))
a = ag.get("agent") or ag
inst = a.get("instructions") or ""
print("agent", a.get("mode"), a.get("channels"), a.get("isPrimary"))
for needle in ["15:30", "R$250", "R$110", "R$50", "até 20 kg", "não citar Gabapentina", "segunda a sábado"]:
    print(" ", needle, needle.lower() in inst.lower() or needle in inst)
