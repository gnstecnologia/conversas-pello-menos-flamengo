# -*- coding: utf-8 -*-
"""Publica prompt + action: só oferecer dentista que trabalha no dia pedido."""
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ENV = Path(r"c:\Users\GC1\Desktop\Automação GHL\.env")
OUT = Path(r"c:\Users\GC1\Desktop\Automação GHL\multiodonto-audit")
key = None
for line in ENV.read_text(encoding="utf-8").splitlines():
    if line.startswith("GHL_MULTIODONTO_API_KEY="):
        key = line.split("=", 1)[1].strip()
        break
assert key, "missing PIT"

AGENT = "3Fzfmx7ViwyD9v16h4DR"
ACTION = "zeWiS2QJD0LcF6UOaejG"
LOC = "3R4hY0j3TJyj2SkmSQL3"
BASE = "https://services.leadconnectorhq.com"

PERSONALITY = (OUT / "personality-new.txt").read_text(encoding="utf-8").strip()
GOAL = (OUT / "goal-new.txt").read_text(encoding="utf-8").strip()
INSTRUCTIONS = (OUT / "instructions-new.txt").read_text(encoding="utf-8").strip()

AI_DESC = (
    "Appointment Booking — Multiodonto clínico geral.\n"
    "PASSO 0: se o paciente disse HOJE/amanhã, converta para o dia da semana da data atual. Não chute. Não use o mapa de ontem.\n"
    "PASSO 1: copie a linha do mapa CG — SIM só esses calendários. 0 slots de quem NÃO trabalha no dia ≠ lotado.\n"
    "NUNCA marcar se convênio=APPAI/Appai/APAI (nem para hoje). NUNCA marcar canal/endodontia.\n"
    "NUNCA Carlos, Leonardo, Giovanna Barra, Rafael Barra.\n"
    "PROIBIDO listar todos os dentistas e depois dizer que não tem vaga. Terça CG: abra SÓ Scherres e mostre horários (não pergunte lista).\n"
    "CG mapa SIM: Seg Giovanna/Rafael | Ter SÓ Scherres | Qua Castro/Rafael | Qui Castro/Giovanna | "
    "Sex Scherres/Thais | Sab Scherres/Castro/Giovanna.\n"
    "CG NÃO: Terça=Castro/Thais/Giovanna/Rafael | Quarta=Scherres/Thais/Giovanna | Sexta=Castro/Giovanna/Rafael | Sábado=Thais/Rafael.\n"
    "Barra: só Juliana seg-qui. Sex/sáb Barra NÃO usar booking — paciente liga (21) 2442-5192 | (21) 95904-2251.\n"
    "Só diga 'sem vaga no dia' depois de consultar o calendário da coluna SIM."
)

CAL_TRIGGERS = [
    {
        "id": "fUvShjVjDVERgGZUuNls",
        "triggerCondition": (
            "Dr Lucas Scherres CG. Usar SOMENTE se o dia pedido (HOJE convertido) for terça OU sexta OU sábado. "
            "Se HOJE=terça: este é o ÚNICO calendário — abrir já e mostrar horários, sem listar outros nomes. "
            "NÃO usar segunda/quarta/quinta."
        ),
    },
    {
        "id": "dpnGTRPb4wLTjWxPfO3M",
        "triggerCondition": (
            "Dr Lucas Castro CG. Usar SOMENTE quarta OU quinta OU sábado. "
            "NUNCA terça (ele não trabalha terça — 0 slots na terça NÃO é lotado). "
            "NUNCA segunda. NUNCA sexta. Se HOJE=terça: NÃO USAR."
        ),
    },
    {
        "id": "bOur6KKgSm1cQvIxYnwQ",
        "triggerCondition": (
            "Dra Thais Campos CG. Usar SOMENTE sexta. "
            "NUNCA terça, NUNCA sábado, NUNCA segunda/quarta/quinta. "
            "Se HOJE=terça: NÃO USAR. 0 slots fora da sexta = ela não trabalha nesse dia."
        ),
    },
    {
        "id": "ACcmwEr9OeexBtiU4yl6",
        "triggerCondition": (
            "Dra Giovanna Ferreira CG. Usar SOMENTE segunda OU quinta OU sábado. "
            "NUNCA terça. NUNCA quarta. NUNCA sexta. NÃO usar na Barra. "
            "Se HOJE=terça: NÃO USAR."
        ),
    },
    {
        "id": "Sq4S1RHRaAoVfLbcb6Gj",
        "triggerCondition": (
            "Dr Rafael Ramos CG. Usar SOMENTE segunda OU quarta. "
            "NUNCA terça. NUNCA quinta. NUNCA sexta. NUNCA sábado. NÃO usar na Barra. "
            "Se HOJE=terça: NÃO USAR."
        ),
    },
    {
        "id": "1X5AaBX8WCmn4FpAuMxJ",
        "triggerCondition": (
            "Dra Juliana Cardoso Barra. Usar SOMENTE Barra + segunda OU terça OU quarta OU quinta. "
            "NUNCA sexta nem sábado (nesses dias só ligação)."
        ),
    },
]


def req(method, path, body=None):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {key}",
            "Version": "2021-07-28",
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")


def unwrap_agent(payload):
    if isinstance(payload, dict) and "instructions" in payload:
        return payload
    if isinstance(payload, dict):
        return payload.get("data") or payload.get("agent") or payload
    return payload


def main():
    st, agent = req("GET", f"/conversation-ai/agents/{AGENT}")
    print("GET agent", st)
    if st != 200:
        print(agent)
        return
    a = unwrap_agent(agent)
    (OUT / "agent-before-dentista-dia.json").write_text(
        json.dumps(a, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("before isPrimary:", a.get("isPrimary"), "mode:", a.get("mode"), "channels:", a.get("channels"))

    channels = list(a.get("channels") or [])
    for ch in ("SMS", "WhatsApp", "IG", "FB"):
        if ch not in channels:
            channels.append(ch)

    put_body = {
        "name": a.get("name") or "Letícia IA Agendamento",
        "personality": PERSONALITY,
        "goal": GOAL,
        "instructions": INSTRUCTIONS,
        "isPrimary": True,
        "mode": a.get("mode") or "auto-pilot",
        "channels": channels,
    }
    for f in ("mode", "knowledgeBaseIds", "autoPilotMaxMessages"):
        if a.get(f) is not None:
            put_body[f] = a[f]
    put_body["isPrimary"] = True

    st, resp = req("PUT", f"/conversation-ai/agents/{AGENT}", put_body)
    print("PUT agent", st)
    if st not in (200, 201):
        print(str(resp)[:2000])
        return
    (OUT / "agent-after-dentista-dia.json").write_text(
        json.dumps(resp, ensure_ascii=False, indent=2) if isinstance(resp, dict) else str(resp),
        encoding="utf-8",
    )
    (OUT / "leticia-prompt.txt").write_text(
        "PERSONALITY\n" + PERSONALITY + "\n\nGOAL\n" + GOAL + "\n\nINSTRUCTIONS\n" + INSTRUCTIONS,
        encoding="utf-8",
    )

    st, agent2 = req("GET", f"/conversation-ai/agents/{AGENT}")
    a2 = unwrap_agent(agent2)
    instr = a2.get("instructions") or ""
    print("VERIFY isPrimary:", a2.get("isPrimary"), "mode:", a2.get("mode"), "channels:", a2.get("channels"))
    checks = {
        "ERRO GRAVE dentista dia": "ERRO GRAVE 01/09/2026" in instr,
        "mapa SIM terça": "Terça: SIM Scherres" in instr,
        "coluna NÃO": "NÃO Castro, Thais, Giovanna, Rafael" in instr,
        "SMS": "SMS" in (a2.get("channels") or []),
        "WhatsApp": "WhatsApp" in (a2.get("channels") or []),
        "canal so particular": "NÃO realizamos para NENHUM convênio" in instr,
        "APPAI bloqueio": "APPAI — BLOQUEIO ABSOLUTO" in instr,
        "isPrimary True": a2.get("isPrimary") is True,
    }
    for k, v in checks.items():
        print(f"  {k}: {v}")
    if a2.get("isPrimary") is not True:
        print("ALERTA: isPrimary caiu — restaurando")
        st, resp3 = req("PUT", f"/conversation-ai/agents/{AGENT}", put_body)
        print("PUT restore", st)
        st, agent2 = req("GET", f"/conversation-ai/agents/{AGENT}")
        a2 = unwrap_agent(agent2)
        print("GET after restore isPrimary:", a2.get("isPrimary"), "channels:", a2.get("channels"))
        if a2.get("isPrimary") is not True:
            print("ALERTA: isPrimary continua falso")

    st, search = req("GET", f"/conversation-ai/agents/search?locationId={LOC}&limit=20")
    print("SEARCH", st)
    agents = []
    if isinstance(search, dict):
        agents = (
            search.get("agents")
            or (search.get("data") or {}).get("agents")
            or search.get("data")
            or []
        )
        if isinstance(agents, dict):
            agents = agents.get("agents") or []
    if isinstance(agents, list):
        for ag in agents:
            if isinstance(ag, dict):
                print(
                    " search:",
                    ag.get("name"),
                    ag.get("id"),
                    "primary=",
                    ag.get("isPrimary"),
                    "mode=",
                    ag.get("mode"),
                )
                if ag.get("id") == AGENT and ag.get("isPrimary") is not True:
                    print("ALERTA SEARCH: Letícia não está isPrimary")

    st, cur = req("GET", f"/conversation-ai/agents/{AGENT}/actions/{ACTION}")
    print("GET action", st)
    if st != 200:
        print(cur)
        return
    data = cur["data"] if isinstance(cur, dict) and "data" in cur else cur
    details = data["details"]
    body = {
        "name": data.get("name") or "Appointment Booking Action",
        "type": data.get("type") or "appointmentBooking",
        "details": {
            "calendarIds": CAL_TRIGGERS,
            "calendarId": CAL_TRIGGERS[0]["id"],
            "calendarActionType": details.get("calendarActionType") or "multiple",
            "aiDescription": AI_DESC,
            "fallbackCalendar": bool(details.get("fallbackCalendar")),
            "fallbackCalendarId": details.get("fallbackCalendarId") or "",
            "onlySendLink": bool(details.get("onlySendLink")),
            "triggerWorkflow": False,
            "sleepAfterBooking": bool(details.get("sleepAfterBooking")),
            "transferBot": bool(details.get("transferBot")),
            "rescheduleEnabled": bool(details.get("rescheduleEnabled", True)),
            "cancelEnabled": bool(details.get("cancelEnabled", True)),
        },
    }
    st, resp = req("PUT", f"/conversation-ai/agents/{AGENT}/actions/{ACTION}", body)
    print("PUT action", st)
    if st not in (200, 201):
        print(str(resp)[:1500])
        return

    st, cur2 = req("GET", f"/conversation-ai/agents/{AGENT}/actions/{ACTION}")
    data2 = cur2["data"] if isinstance(cur2, dict) and "data" in cur2 else cur2
    desc = data2["details"].get("aiDescription") or ""
    ids = [c["id"] for c in data2["details"]["calendarIds"]]
    print("VERIFY action terça SÓ Scherres:", "Ter SÓ Scherres" in desc or "terça CG: abra SÓ Scherres" in desc)
    print("VERIFY action HOJE convert:", "HOJE" in desc)
    print("VERIFY action 0 slots:", "0 slots" in desc)
    print("VERIFY cals", ids)
    for c in data2["details"]["calendarIds"]:
        print(" -", c["id"], "|", (c.get("triggerCondition") or "")[:90])


if __name__ == "__main__":
    main()
