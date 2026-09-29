# -*- coding: utf-8 -*-
import json, sys, urllib.request, urllib.error
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ENV = Path(r"c:\Users\GC1\Desktop\Automação GHL\.env")
OUT = Path(r"c:\Users\GC1\Desktop\Automação GHL\multiodonto-audit")
key = None
for line in ENV.read_text(encoding="utf-8").splitlines():
    if line.startswith("GHL_MULTIODONTO_API_KEY="):
        key = line.split("=", 1)[1].strip()
        break
AGENT = "3Fzfmx7ViwyD9v16h4DR"
H = {
    "Authorization": f"Bearer {key}",
    "Version": "2021-07-28",
    "Accept": "application/json",
    "Content-Type": "application/json; charset=utf-8",
    "User-Agent": "Mozilla/5.0",
    "Location-Id": "3R4hY0j3TJyj2SkmSQL3",
}

def req(method, path, body=None):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    r = urllib.request.Request("https://services.leadconnectorhq.com" + path, data=data, method=method, headers=H)
    try:
        with urllib.request.urlopen(r, timeout=90) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")[:1000]

# try minimal isPrimary restore
st, a = req("GET", f"/conversation-ai/agents/{AGENT}")
print("GET", st, "instr ERRO GRAVE", "ERRO GRAVE 01/09/2026" in (a.get("instructions") or ""), "mode", a.get("mode"))
print("GET keys", sorted(a.keys()) if isinstance(a, dict) else type(a))

bodies = [
    {"isPrimary": True, "mode": "auto-pilot", "name": "Letícia IA Agendamento"},
    {"isPrimary": True},
]
for i, b in enumerate(bodies):
    st, r = req("PUT", f"/conversation-ai/agents/{AGENT}", b)
    print(f"\nPUT min {i}", st)
    if isinstance(r, dict):
        print(" keys", [k for k in r.keys() if "prim" in k.lower() or k in ("mode", "channels", "name")])
        print(" isPrimary", r.get("isPrimary"), "mode", r.get("mode"), "channels", r.get("channels"))
    else:
        print(str(r)[:400])

st, s = req("GET", "/conversation-ai/agents/search?limit=20")
print("\nSEARCH after")
for ag in (s.get("agents") or []) if isinstance(s, dict) else []:
    print(ag.get("name"), "mode", ag.get("mode"), "top", ag.get("isPrimary"), "ch", ag.get("channels"))

# confirm prompt still there
st, a2 = req("GET", f"/conversation-ai/agents/{AGENT}")
instr = a2.get("instructions") or ""
print("\nPROMPT still ERRO GRAVE", "ERRO GRAVE 01/09/2026" in instr)
print("mapa terça SIM", "Terça: SIM Scherres" in instr)
print("personality HOJE", "HOJE" in (a2.get("personality") or ""))
print("mode", a2.get("mode"), "channels", a2.get("channels"))
