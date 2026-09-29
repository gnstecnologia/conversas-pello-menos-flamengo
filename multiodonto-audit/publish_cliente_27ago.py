# -*- coding: utf-8 -*-
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
BASE = "https://services.leadconnectorhq.com"

PERSONALITY = (OUT / "personality-new.txt").read_text(encoding="utf-8").strip()
GOAL = (OUT / "goal-new.txt").read_text(encoding="utf-8").strip()
INSTRUCTIONS = (OUT / "instructions-new.txt").read_text(encoding="utf-8").strip()

AI_DESC = (
    "Appointment Booking — Multiodonto clínico geral.\n"
    "ANTES de abrir qualquer calendário: unidade + convênio JÁ validado + dia/data + profissional que ATENDE nesse dia.\n"
    "NUNCA marcar se convênio=APPAI/Appai/APAI (nem para hoje, nem urgente). NUNCA marcar canal/endodontia.\n"
    "NUNCA marcar extração. Só siso incluso/semi-incluso existe (Campo Grande + telefone). Extração comum NÃO fazemos — NÃO oferecer clínico geral.\n"
    "NUNCA Carlos, Leonardo, Giovanna Barra, Rafael Barra.\n"
    "PROIBIDO listar todos os dentistas da especialidade e depois dizer que não atende no dia.\n"
    "Campo Grande mapa: Seg Giovanna/Rafael | Ter Scherres | Qua Castro/Rafael | Qui Castro/Giovanna | "
    "Sex Scherres/Thais | Sab Scherres/Castro/Giovanna (sem Thais/Rafael).\n"
    "Barra: só Juliana seg-qui. Sex/sáb Barra NÃO usar booking — paciente liga (21) 2442-5192 | (21) 95904-2251."
)


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
    (OUT / "agent-before-cliente-27ago.json").write_text(
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

    st, resp = req("PUT", f"/conversation-ai/agents/{AGENT}", put_body)
    print("PUT agent", st)
    if st not in (200, 201):
        print(str(resp)[:2000])
        return
    (OUT / "agent-after-cliente-27ago.json").write_text(
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
        "sem Bianca": "Bianca" not in instr and "Bianca" not in (a2.get("personality") or "") and "Bianca" not in (a2.get("goal") or ""),
        "SMS": "SMS" in (a2.get("channels") or []),
        "WhatsApp": "WhatsApp" in (a2.get("channels") or []),
        "canal so particular": "NÃO realizamos para NENHUM convênio" in instr,
        "canal so ligacao": "PRECISA LIGAR" in instr,
        "siso so CG": "SÓ CAMPO GRANDE" in instr and "siso" in instr.lower(),
        "siso nao Juliana": "NÃO oferecer Dra. Juliana" in instr,
        "extracao so siso": "NÃO faz extração de dente comum" in instr,
        "nao clinico extracao": "NÃO dizer que o clínico geral faz extração" in instr,
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
        instr = a2.get("instructions") or ""
        print("GET after restore isPrimary:", a2.get("isPrimary"), "channels:", a2.get("channels"))
        if a2.get("isPrimary") is not True:
            print("ALERTA: isPrimary continua falso")

    st, cur = req("GET", f"/conversation-ai/agents/{AGENT}/actions/{ACTION}")
    print("GET action", st)
    if st != 200:
        print(cur)
        return
    data = cur["data"] if isinstance(cur, dict) and "data" in cur else cur
    details = data["details"]
    new_cals = [
        {"id": c["id"], "triggerCondition": c.get("triggerCondition") or ""}
        for c in details["calendarIds"]
    ]
    body = {
        "name": data.get("name") or "Appointment Booking Action",
        "type": data.get("type") or "appointmentBooking",
        "details": {
            "calendarIds": new_cals,
            "calendarId": new_cals[0]["id"],
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
    print("VERIFY action APPAI in desc:", "APPAI" in desc)
    print("VERIFY action sem Bianca:", "Bianca" not in desc)
    print("VERIFY action canal in desc:", "canal" in desc.lower() or "endodont" in desc.lower())
    print("VERIFY cals", ids)


if __name__ == "__main__":
    main()
