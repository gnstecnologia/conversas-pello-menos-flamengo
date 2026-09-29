# -*- coding: utf-8 -*-
"""Bloqueia telefone/email de financeiro no prompt EH e define fluxo correto."""
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

FINANCEIRO_BLOCK = """
### 4) Financeiro / setor financeiro / cobrança / boleto / NF financeira
Se o lead disser que é do **financeiro**, ou pedir contato do financeiro, cobrança, boleto, nota fiscal financeira, pagamento, etc.:

**PROIBIDO:**
- Enviar número de WhatsApp
- Enviar e-mail
- Encaminhar para outro telefone/canal
- Inventar contato de financeiro

**Todas as demandas de financeiro são resolvidas neste mesmo WhatsApp do robô.**

Fluxo obrigatório (uma pergunta por vez):

**1ª resposta:**
"Claro! Pode me contar qual é a sua demanda do financeiro? Assim eu encaminho para o responsável certo 😊"

**Depois que o lead explicar a demanda:**
- Salvar {{contact.inteno_do_contato}} = "Financeiro - [resumo curto da demanda]"
- Se ainda não tiver nome: pedir nome completo uma vez e salvar {{contact.nome_completo}}

**Encerramento (horário comercial):**
"Perfeito, [Nome]! Anotei sua demanda. Um responsável do financeiro vai entrar em contato por aqui neste mesmo WhatsApp para te ajudar."

**Encerramento (fim de semana ou fora do horário comercial):**
"Perfeito, [Nome]! Anotei sua demanda. Como estamos fora do horário comercial, um responsável do financeiro retorna o contato neste mesmo WhatsApp no **próximo horário comercial**."

AÇÃO: encaminhar para o responsável/humano interno, sem passar outro número ou e-mail.
"""

ABSOLUTE_EXTRA = """
- NUNCA envie telefone, WhatsApp ou e-mail do financeiro (nem de nenhum outro setor) para o lead.
- Demandas de financeiro ficam neste mesmo número do robô: perguntar a demanda e avisar que um responsável entrará em contato.
"""


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
            return resp.status, json.loads(resp.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")


def main():
    code, data = req("GET", f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}")
    print("GET", code)
    a = data.get("agent") if isinstance(data, dict) else None
    if not isinstance(a, dict):
        a = data if isinstance(data, dict) else {}
    inst = a.get("instructions") or ""
    print("len before", len(inst), "primary", a.get("isPrimary"))

    # remove old financeiro block if re-running
    if "### 4) Financeiro" in inst:
        # replace from ### 4) until next ### or ### IMPORTANTE
        start = inst.find("### 4) Financeiro")
        end_markers = ["\n### IMPORTANTE", "\n### 5)", "\n## RESTRIÇÕES"]
        end = len(inst)
        for m in end_markers:
            i = inst.find(m, start + 1)
            if i != -1:
                end = min(end, i)
        inst = inst[:start] + FINANCEIRO_BLOCK.strip() + "\n\n" + inst[end:].lstrip()
        print("replaced existing financeiro block")
    else:
        marker = "### IMPORTANTE\n- Fora dessas mensagens/contextos específicos"
        if marker not in inst:
            raise SystemExit("IMPORTANTE marker not found")
        inst = inst.replace(marker, FINANCEIRO_BLOCK.strip() + "\n\n" + marker)
        print("inserted financeiro block")

    # add absolute restrictions if missing
    if "NUNCA envie telefone, WhatsApp ou e-mail do financeiro" not in inst:
        anchor = "- Salvar sempre a variável IMEDIATAMENTE após receber a resposta,\n  antes de avançar para a próxima pergunta."
        if anchor in inst:
            inst = inst.replace(anchor, anchor + ABSOLUTE_EXTRA)
        else:
            # try shorter anchor
            alt = "- Salvar sempre a variável IMEDIATAMENTE após receber a resposta,"
            if alt in inst:
                # insert after RESTRIÇÕES section end before ---
                idx = inst.find(alt)
                nl = inst.find("\n---", idx)
                if nl != -1:
                    inst = inst[:nl] + ABSOLUTE_EXTRA + inst[nl:]
                else:
                    inst = inst + ABSOLUTE_EXTRA
            else:
                inst = inst + "\n## RESTRIÇÃO FINANCEIRO\n" + ABSOLUTE_EXTRA

    payload = {
        "name": a.get("name"),
        "personality": a.get("personality"),
        "goal": a.get("goal"),
        "instructions": inst,
        "isPrimary": True,
        "mode": a.get("mode") or "auto-pilot",
    }
    if a.get("channels") is not None:
        payload["channels"] = a.get("channels")
    if a.get("knowledgeBaseIds") is not None:
        payload["knowledgeBaseIds"] = a.get("knowledgeBaseIds")

    code2, body2 = req("PUT", f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}", payload)
    print("PUT", code2, type(body2).__name__)
    if isinstance(body2, str):
        print(body2[:500])
        raise SystemExit("PUT failed")

    code3, data3 = req("GET", f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}")
    a3 = data3.get("agent") or data3
    inst3 = a3.get("instructions") or ""
    print("GET after", code3, "primary", a3.get("isPrimary"), "len", len(inst3))
    print("has financeiro block", "### 4) Financeiro" in inst3)
    print("has ban phone/email", "NUNCA envie telefone" in inst3)
    (OUT / "ehmedical-system-prompt.txt").write_text(
        "===== PERSONALITY =====\n"
        + (a3.get("personality") or "")
        + "\n\n===== GOAL =====\n"
        + (a3.get("goal") or "")
        + "\n\n===== INSTRUCTIONS =====\n"
        + inst3,
        encoding="utf-8",
    )
    print("saved")


if __name__ == "__main__":
    main()
