# -*- coding: utf-8 -*-
"""Atualiza prompt EHMEDICAL: Nova America + locacao so RJ."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

ENV = Path(r"c:\Users\GC1\Desktop\Automação GHL\.env")
OUT = Path(r"c:\Users\GC1\Desktop\Automação GHL\gamma-vet")
vals = {}
for line in ENV.read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()

KEY = vals["GHL_EHMEDICAL_API_KEY"]
AGENT = "X4ctLzGA1JxYDopKofGa"


def req(method, url, body=None):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    r = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {KEY}",
            "Version": "2021-07-28",
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "Mozilla/5.0",
        },
    )
    try:
        with urllib.request.urlopen(r, timeout=90) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(err)
        except Exception:
            return e.code, err


OLD_LOC = """## ETAPA 2B — LOCAÇÃO (opção 2)

Objetivo: coletar 2 dados antes de encaminhar ao Time de Locação.
Regra obrigatória: locação nunca passa pelo SDR. Sempre direto
para o Time de Locação.

### Pergunta 1 — Nome completo

BOT: "Claro! Vou te ajudar com a locação de equipamento 😊
Qual é o seu nome completo?"

AÇÃO ao receber resposta: salvar {{contact.nome_completo}} = resposta do lead.

### Pergunta 2 — Região ou cidade

BOT: "Obrigado(a), [Nome]!
Em qual região ou cidade você atende?"

AÇÃO ao receber resposta: salvar {{contact.regio__cidade}} = resposta do lead.

### Encerramento

**Segunda a sexta:**
BOT: "Perfeito, [Nome]! 😊
Vou te conectar agora com nosso time de locação.
Um especialista vai te atender em instantes!"

**Sábado e domingo:**
BOT: "Perfeito, [Nome]! 😊
Registramos suas informações para locação.
Como estamos no fim de semana, nosso time retorna o contato **na segunda-feira**, em horário comercial.
Obrigada pela paciência!"

AÇÃO: encaminhar para o Time de Locação. Nunca passa pelo SDR."""

NEW_LOC = """## ETAPA 2B — LOCAÇÃO (opção 2)

Objetivo: coletar 2 dados antes de encaminhar ao Time de Locação.
Regra obrigatória: locação nunca passa pelo SDR. Sempre direto
para o Time de Locação.

**REGRA DE ABRANGÊNCIA (obrigatória):**
- A Eh Medical atua com **locação de equipamentos somente na cidade do Rio de Janeiro (RJ)**.
- Deixe isso claro já na primeira resposta de locação.
- Se o lead estiver em outro estado/cidade, explique com educação que a locação é apenas no Rio de Janeiro e pergunte se mesmo assim deseja continuar o atendimento / falar com o time.

### Pergunta 1 — Nome completo

BOT: "Claro! Vou te ajudar com a locação de equipamento 😊
Atuamos com locação **somente na cidade do Rio de Janeiro (RJ)**.
Qual é o seu nome completo?"

AÇÃO ao receber resposta: salvar {{contact.nome_completo}} = resposta do lead.

### Pergunta 2 — Região no Rio de Janeiro

BOT: "Obrigado(a), [Nome]!
Em qual região do **Rio de Janeiro** você precisa da locação?
(Ex.: Zona Sul, Barra, Centro, Jacarepaguá, etc.)"

AÇÃO ao receber resposta: salvar {{contact.regio__cidade}} = resposta do lead.

Se o lead informar outra cidade/estado (fora do Rio de Janeiro):
BOT: "Entendi! Só reforçando: nossa locação de equipamentos atende **apenas a cidade do Rio de Janeiro**.
Posso te encaminhar mesmo assim para nosso time de locação te orientar?"
- Se sim → seguir para o encerramento / encaminhar Time de Locação.
- Se não → agradecer e encerrar com educação.

### Encerramento

**Segunda a sexta (horário comercial):**
BOT: "Perfeito, [Nome]! 😊
Vou te conectar agora com nosso time de locação no Rio de Janeiro.
Um especialista vai te atender em instantes!"

**Sábado, domingo ou fora do horário comercial:**
BOT: "Perfeito, [Nome]! 😊
Registramos suas informações para locação no Rio de Janeiro.
Como estamos fora do horário comercial, nosso time retorna o contato no **próximo horário comercial**.
Obrigada pela paciência!"

AÇÃO: encaminhar para o Time de Locação. Nunca passa pelo SDR."""

NOVA_AMERICA = """
### 3) Aluguel / locação da sala comercial do Nova América
Se o lead pedir informações sobre aluguel/locação da **sala do Nova América** (ex.: "informações sobre o aluguel da sala do Nova América", "sala comercial Nova América", "locação sala Nova América"), NÃO abrir o menu padrão e NÃO seguir o fluxo de locação de equipamentos.

Fluxo obrigatório (uma mensagem por vez):

**1ª resposta do bot (sempre):**
"Oi! Tudo bem? 😊 Vi que você se interessou pela sala comercial do Nova América. Ela está disponível para locação! Podemos te passar mais informações sobre o imóvel. O que você gostaria de saber?"

**Depois da resposta do lead → pedir nome:**
"Perfeito! Para dar continuidade ao seu atendimento, poderia me informar seu nome completo, por favor?"
AÇÃO ao receber: salvar {{contact.nome_completo}} = resposta do lead.
AÇÃO: salvar {{contact.inteno_do_contato}} = "Locação sala Nova América".

**Encerramento após o nome:**

- **Segunda a sexta, em horário comercial:**
"Perfeito, [Nome]! 😊 Obrigado pelas informações. Vou encaminhar seu contato para o nosso consultor responsável, que dará continuidade ao atendimento e poderá te passar todos os detalhes sobre a locação da sala."

- **Final de semana OU fora do horário comercial:**
"Perfeito, [Nome]! 😊 Obrigado pelas informações. Registramos seu interesse na sala comercial do Nova América.
Como estamos fora do horário comercial, nosso consultor responsável retorna o contato no **próximo horário comercial** e poderá te passar todos os detalhes sobre a locação da sala.
Obrigada pela paciência!"

AÇÃO: encaminhar para o consultor/time responsável pela locação da sala (Time de Locação). Não misturar com o fluxo de locação de equipamentos médicos.
"""


def main():
    code, data = req("GET", f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}")
    print("GET", code)
    a = data.get("agent") or data
    inst = a.get("instructions") or ""
    print("instructions len before", len(inst))
    print("isPrimary", a.get("isPrimary"), "mode", a.get("mode"))

    if OLD_LOC not in inst:
        raise SystemExit("OLD_LOC block not found — abort")
    inst = inst.replace(OLD_LOC, NEW_LOC)

    # insert Nova America before the ### IMPORTANTE at end of extras
    marker = "### IMPORTANTE\n- Fora dessas mensagens/contextos específicos"
    if "Nova América" in inst or "Nova America" in inst:
        print("Nova America already present — skip insert if duplicated")
        if "sala comercial do Nova América" not in inst:
            if marker not in inst:
                raise SystemExit("IMPORTANTE marker not found")
            inst = inst.replace(marker, NOVA_AMERICA.strip() + "\n\n" + marker)
    else:
        if marker not in inst:
            raise SystemExit("IMPORTANTE marker not found")
        inst = inst.replace(marker, NOVA_AMERICA.strip() + "\n\n" + marker)

    # also reinforce weekend section covers fora do horario for extras
    weekend_note = (
        "\n- Para campanhas específicas (ex.: sala Nova América), use o mesmo gatilho "
        "de **próximo horário comercial** quando for final de semana OU fora do horário comercial."
    )
    if "sala Nova América" not in (a.get("instructions") or "") and weekend_note.strip() not in inst:
        anchor = "- **Segunda a sexta**: use as mensagens de encerramento padrão de cada etapa."
        if anchor in inst:
            inst = inst.replace(anchor, anchor + weekend_note)

    payload = {
        "name": a.get("name"),
        "personality": a.get("personality"),
        "goal": a.get("goal"),
        "instructions": inst,
        "isPrimary": True if a.get("isPrimary") else a.get("isPrimary"),
        "mode": a.get("mode") or "auto-pilot",
    }
    # preserve channels if present
    if a.get("channels") is not None:
        payload["channels"] = a.get("channels")

    # force primary true since it is the primary agent
    if a.get("isPrimary"):
        payload["isPrimary"] = True

    code2, body2 = req("PUT", f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}", payload)
    print("PUT", code2, str(body2)[:500] if not isinstance(body2, dict) else list(body2.keys()))

    # verify
    code3, data3 = req("GET", f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}")
    a3 = data3.get("agent") or data3
    inst3 = a3.get("instructions") or ""
    print("GET after", code3)
    print("isPrimary after", a3.get("isPrimary"), "mode", a3.get("mode"))
    print("len after", len(inst3))
    print("has Nova America", "Nova América" in inst3)
    print("has RJ only", "somente na cidade do Rio de Janeiro" in inst3)
    (OUT / "ehmedical-system-prompt.txt").write_text(
        "===== PERSONALITY =====\n"
        + (a3.get("personality") or "")
        + "\n\n===== GOAL =====\n"
        + (a3.get("goal") or "")
        + "\n\n===== INSTRUCTIONS =====\n"
        + inst3,
        encoding="utf-8",
    )
    print("saved prompt file")


if __name__ == "__main__":
    main()
