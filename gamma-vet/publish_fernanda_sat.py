# -*- coding: utf-8 -*-
"""Publica prompt, booking e FAQ dos sábados intercalados da Fernanda. isPrimary true."""
import json
import subprocess
import urllib.request
import urllib.error
from pathlib import Path

OUT = Path(r"c:\Users\GC1\Desktop\Automação GHL\gamma-vet")
ENV = Path(r"c:\Users\GC1\Desktop\Automação GHL\.env")
vals = {}
for line in ENV.read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()

KEY = vals["GHL_GAMMA_API_KEY"]
LOC = vals["GHL_GAMMA_LOCATION_ID"]
AGENT = vals["GHL_GAMMA_AGENT_ID"]
KB = vals["GHL_GAMMA_KB_ID"]
BOOKING = "g4K4spRJdKq1zpMr2LLb"
UA = "Mozilla/5.0"


def req(method, url, body=None, version="2021-07-28"):
    data = None if body is None else json.dumps(body).encode("utf-8")
    r = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {KEY}",
            "Version": version,
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": UA,
        },
    )
    try:
        with urllib.request.urlopen(r, timeout=90) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(err)
        except Exception:
            parsed = err
        return e.code, parsed


md = (OUT / "Procedimentos_GammaVet_KB.md").read_text(encoding="utf-8")
(OUT / "Procedimentos_GammaVet_KB.txt").write_text(md, encoding="utf-8")
instructions = (OUT / "system-prompt-completo.md").read_text(encoding="utf-8")

print("=== agent ===")
code, body = req(
    "PUT",
    f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}",
    {
        "name": "Assistente Gamma Vet",
        "isPrimary": True,
        "mode": "off",
        "instructions": instructions,
        "goal": (
            "Conduzir o responsável até o agendamento do exame: na primeira resposta já entregar o pacote "
            "(dias, valor, sinal, preparo, exames prévios); coletar dados; consultar agenda real no calendário "
            "correto; oferecer horários só nos dias permitidos e confirmar no sistema. "
            "Não oferecer Fernanda na quinta; sábados da Fernanda só se a agenda tiver slot (intercalados). "
            "Não oferecer cintilo fora de seg/qui nem radioiodo antes da cintilo de tireoide. Em dúvida, transferir."
        ),
        "personality": (
            "Formal porém acolhedor. Use animalzinho, seu pet e responsável pelo paciente. "
            "Fale do Gamma Vet no masculino (o centro). Sempre se apresente como assistente virtual do Gamma Vet. "
            "Agradeça a preferência. Respostas curtas, claras, estilo WhatsApp, em português do Brasil. "
            "Áudio: peça texto; você não transcreve áudio de WhatsApp."
        ),
        "knowledgeBaseIds": [KB],
        "channels": ["WebChat"],
        "autoPilotMaxMessages": 100,
        "sleepEnabled": False,
        "sleepOnManualMessage": True,
        "sleepOnWorkflowMessage": False,
    },
)
print("PUT", code, body.get("message") if isinstance(body, dict) else str(body)[:200])
code, agent = req("GET", f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}")
agent = agent.get("agent", agent) if isinstance(agent, dict) else {}
inst = agent.get("instructions") or ""
print("isPrimary", agent.get("isPrimary"), "intercalados", "intercalados" in inst)
(OUT / "agent-live-now.json").write_text(json.dumps(agent, ensure_ascii=False, indent=2), encoding="utf-8")

print("=== booking ===")
code, raw = req(
    "GET",
    f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}/actions/{BOOKING}",
    version="2021-04-15",
)
action = raw.get("data", raw) if isinstance(raw, dict) else {}
details = dict(action.get("details") or {})
cals = list(details.get("calendarIds") or [])
for c in cals:
    if c.get("id") == "LuylqTlDWQcpnmeslByJ":
        c["triggerCondition"] = (
            "Ultrassonografia / US / abdominal / cervical / microbolhas / cistocentese com Dra. Fernanda. "
            "Fernanda: segunda, terça, quarta e sexta. NÃO usar na quinta. "
            "Sábados intercalados (22/08/2026 aberto, 29/08/2026 fechado, e segue). "
            "Só oferecer sábado se a ferramenta devolver slot."
        )
details["calendarIds"] = cals
details["aiDescription"] = (
    "Agenda exames do Gamma Vet no calendário correto. "
    "US: Dra. Fernanda seg/ter/qua/sex (NUNCA quinta). Sábados da Fernanda intercalados "
    "(22/08 aberto, 29/08 fechado, um sim um não) — só oferecer se houver slot. "
    "Quinta de US = Dra. Luciana. Cintilografia só segunda e quinta. "
    "Radioiodoterapia só depois da cintilo de tireoide (terças). "
    "Na segunda, Fernanda faz US 30 min + RX 30 min + TC 1 h (TC+cito 1h30) — horários não coincidem. "
    "Na primeira resposta, informar dias, valor, sinal, preparo e exames prévios. "
    "Só oferecer horários reais da ferramenta."
)
code, body = req(
    "PUT",
    f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}/actions/{BOOKING}",
    {"type": "appointmentBooking", "name": "Agendamento Gamma Vet", "details": details},
    version="2021-04-15",
)
print("booking PUT", code, body.get("message") if isinstance(body, dict) else "ok")

print("=== FAQ Fernanda ===")
code, data = req(
    "GET",
    f"https://services.leadconnectorhq.com/knowledge-base/faqs?locationId={LOC}&knowledgeBaseId={KB}&limit=100",
)
faqs = (data or {}).get("faqs") or []
answer = (
    "A Dra. Fernanda NÃO atende quinta (atende segunda, terça, quarta e sexta). "
    "Quinta de ultrassonografia é só a Dra. Luciana. "
    "Sábados da Fernanda são intercalados: um sim, um não. "
    "22/08/2026 aberto, 29/08/2026 fechado, e segue esse padrão. Horário de sábado 8h às 14h. "
    "Só oferecer sábado se a agenda real tiver horário."
)
updated = 0
for f in faqs:
    q = (f.get("question") or "").lower()
    if "fernanda" in q and ("quinta" in q or "sábado" in q or "sabado" in q):
        fid = f.get("id") or f.get("_id")
        code, body = req(
            "PUT",
            f"https://services.leadconnectorhq.com/knowledge-base/faqs/{fid}",
            {
                "question": f.get("question"),
                "answer": answer,
                "locationId": LOC,
                "knowledgeBaseId": KB,
            },
        )
        print("faq", code, (f.get("question") or "")[:80])
        updated += 1
if updated == 0:
    code, body = req(
        "POST",
        "https://services.leadconnectorhq.com/knowledge-base/faqs",
        {
            "locationId": LOC,
            "knowledgeBaseId": KB,
            "question": "Dra. Fernanda atende quinta? E sábado?",
            "answer": answer,
        },
    )
    print("faq create", code)

# upload md
cmd = [
    "curl.exe", "-s", "-w", " HTTP:%{http_code}",
    "-X", "POST",
    f"https://services.leadconnectorhq.com/knowledge-base/files?locationId={LOC}&knowledgeBaseId={KB}",
    "-H", f"Authorization: Bearer {KEY}",
    "-H", "Version: 2021-07-28",
    "-H", "Accept: application/json",
    "-H", "User-Agent: Mozilla/5.0",
    "-F", f"file=@{(OUT / 'Procedimentos_GammaVet_KB.md')}",
    "-F", f"locationId={LOC}",
    "-F", f"knowledgeBaseId={KB}",
]
r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
print("md upload", r.stdout[-80:])
print("done primary", agent.get("isPrimary"))
