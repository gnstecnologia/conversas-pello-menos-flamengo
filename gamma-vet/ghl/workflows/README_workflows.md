# Workflows — especificação GHL (Momento 1)

> A API pública não cria workflows completos. Configurar na UI: Automation → Workflows.
> Pipeline necessário: **Agendamento Gamma Vet** (ver `../provisioning/pipeline_stages.json`).

---

## WF-01 — Entrada conversa
**Trigger:** Customer replied / inbound message (WhatsApp)  
**Filtro (fase teste):** Contact has tag `teste_interno` OU phone in whitelist  

**Actions:**
1. If no open opportunity in pipeline Agendamento → Create Opportunity name=`{{contact.name}} — agendamento` stage=`Novo lead`
2. If tag `cliente_ativo` → Update opportunity stage=`Triagem`
3. Add tag `canal_whatsapp` (ou instagram/google conforme origem)
4. Enable Conversation AI agent (se não automático no canal)

---

## WF-02 — Triagem completa → fila setorial
**Trigger:** Contact tag added `pedido_medico_recebido` OR custom field `Procedimento Interesse` updated OR Agent Trigger Workflow "triagem_completa"  

**Conditions / branching:**
- `Setor Destino` = ultrassom → stage `Fila Ultrassom`
- = tomografia → stage `Fila Tomografia` + Add tag `urgencia_tomo` + Internal notification (urgente)
- = cintilografia AND procedimento contém "renal" → stage `Fila Cintilografia` + tag `urgencia_cintilo_renal` + notify urgente
- = cintilografia (demais) → stage `Fila Cintilografia` + tag `prioridade_cintilo`
- = fora_escopo → stage `Exames nao atendidos`
- else → stage `Profissional e horario`

**Then:** Assign to user da recepção / round-robin; optional Pause AI

---

## WF-03 — Fora do horário / Aguardando
**Trigger:** Agent Trigger Workflow "fora_horario" OR Inbound message + custom date/time condition outside recepção (seg–sex 8:30–18; sáb 8–14; dom fechado)

**Actions:**
1. Add tag `aguardando`
2. Opportunity stage = `Aguardando retorno`
3. Send message: "Recebemos sua solicitação. Nossa equipe retoma no primeiro horário útil para confirmar o melhor encaixe."
4. Create internal task for next business morning

---

## WF-04 — Follow-up 5x
**Trigger:** Opportunity stage = `Novo lead` OR `Triagem` AND last customer message older than X (or after AI first reply without progress)

**Sequence (Wait actions):**
1. Wait 15 min → If no reply useful → send FU1 (within IA window + 24h WhatsApp)
2. Wait 1 h → FU2
3. Wait 2 h → FU3
4. Wait 7 h → FU4
5. Wait 12 h → FU5
6. After FU5 sem resposta → stage `Nao responde`

**Guards em cada envio:**
- Current time in [seg–sáb 07–20] OR [dom 10–20]
- Within 24h of last inbound customer message (else stop / use template if approved later)
- Contact not in stage Agendou / Em atendimento / Desqualificado

**Textos sugeridos:** ver `../content/followup_mensagens.md`

---

## WF-05 — Urgência Tomo / Cintilo renal
**Trigger:** Tag added `urgencia_tomo` OR `urgencia_cintilo_renal`

**Actions:**
1. Internal notification (email/SMS/app) para Mari/Marcelo/recepção
2. Opportunity stage already set by WF-02; ensure `Nivel Urgencia` = urgencia
3. Optional: assign high-priority user

---

## WF-06 — Exame fora do escopo
**Trigger:** Agent Trigger Workflow "fora_escopo" OR tag/field Setor = fora_escopo

**Actions:**
1. Stage `Exames nao atendidos`
2. Remove urgency tags if any
3. Optional soft follow-up later for other exams (não urgente)

---

## WF-07 — Handoff humano
**Trigger:** Agent Trigger Workflow "handoff" OR conversation transferred

**Actions:**
1. Stage `Em atendimento`
2. Assign user
3. Pause Conversation AI
4. Internal notify assignee

---

## WF-08 — Agendou (KPI)
**Trigger:** Opportunity stage changed to `Agendou` OR appointment booked by staff

**Actions:**
1. Set opportunity status won (se aplicável)
2. Remove tags `aguardando`, `pedido_medico_pendente`
3. Send confirmação + preparo (se houver)
4. Schedule D-1 reminder: texto tipo **lembrete** (não "confirmação") + preparo

---

## WF-09 — Whitelist teste
**Trigger:** Inbound message

**If** phone NOT in whitelist AND NOT tag `teste_interno`:
- Stop / do not run AI (or route only to human) — até go-live Fase 4

**Whitelist placeholder phones:** ver `../provisioning/import_clientes_ativos_modelo.csv`

---

## Checklist UI de criação
- [ ] Criar pipeline com 13 estágios
- [ ] Criar WF-01 … WF-09
- [ ] Conectar agente às actions Trigger Workflow com nomes: `triagem_completa`, `fora_horario`, `fora_escopo`, `handoff`
- [ ] Testar com contato `teste_interno`
