# -*- coding: utf-8 -*-
import json
import urllib.request

ENV = r"c:\Users\GC1\Desktop\Automação GHL\.env"
vals = {}
with open(ENV, encoding="utf-8") as f:
    for line in f:
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            vals[k.strip()] = v.strip()

key = vals["GHL_GAMMA_API_KEY"]
agent_id = vals["GHL_GAMMA_AGENT_ID"]
UA = "Mozilla/5.0"


def req(url):
    r = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {key}",
            "Version": "2021-07-28",
            "Accept": "application/json",
            "User-Agent": UA,
        },
    )
    with urllib.request.urlopen(r, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


a = req(f"https://services.leadconnectorhq.com/conversation-ai/agents/{agent_id}")
agent = a.get("agent", a)
out = r"c:\Users\GC1\Desktop\Automação GHL\gamma-vet\agent-live-now.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(agent, f, ensure_ascii=False, indent=2)

print("name:", agent.get("name"))
print("primary:", agent.get("isPrimary"))
print("mode:", agent.get("mode"))
print("kb:", agent.get("knowledgeBaseIds"))
print("actions:", len(agent.get("actions") or []))
for act in agent.get("actions") or []:
    print(" -", act.get("type"), act.get("id"), act.get("name", ""))
inst = agent.get("instructions") or ""
print("instructions len:", len(inst))
print("goal:", (agent.get("goal") or "")[:300])
print("personality:", (agent.get("personality") or "")[:200])
print("--- instructions head ---")
print(inst[:800])
print("--- instructions tail ---")
print(inst[-400:])
