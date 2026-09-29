# -*- coding: utf-8 -*-
import json
import sys
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ENV = Path(r"c:\Users\GC1\Desktop\Automação GHL\.env")
key = None
for line in ENV.read_text(encoding="utf-8").splitlines():
    if line.startswith("GHL_MULTIODONTO_API_KEY="):
        key = line.split("=", 1)[1].strip()
        break

AGENT = "3Fzfmx7ViwyD9v16h4DR"
ACTION = "zeWiS2QJD0LcF6UOaejG"
h = {
    "Authorization": f"Bearer {key}",
    "Version": "2021-07-28",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0",
}


def get(url):
    r = urllib.request.Request(url, headers=h)
    return json.loads(urllib.request.urlopen(r, timeout=60).read().decode())


a = get(f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}")
inst = a.get("instructions") or ""
print("isPrimary", a.get("isPrimary"))
print("mode", a.get("mode"))
print("channels", a.get("channels"))
print("Bianca sai:", "NÃO faz mais parte da equipe" in inst)
print("canal nenhum convenio:", "NÃO realizamos para NENHUM convênio" in inst)
print("canal ligar:", "PRECISA LIGAR" in inst)
print("APPAI bloqueio:", "APPAI — BLOQUEIO ABSOLUTO" in inst)
print("convênio antes da agenda:", "ANTES de listar dentista" in inst)

act = get(f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}/actions/{ACTION}")
d = (act.get("data") or act)["details"]
desc = d.get("aiDescription") or ""
ids = [c["id"] for c in d["calendarIds"]]
print("action APPAI", "APPAI" in desc)
print("action Bianca", "Bianca" in desc)
print("action canal", "canal" in desc.lower())
print("cals", ids)
print("cals count", len(ids))
