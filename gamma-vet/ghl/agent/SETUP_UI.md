# Setup do Agente Conversation AI (UI) — Momento 1

A API `POST /conversation-ai/agents` exige schema específico pouco documentado publicamente; criar o agente na UI e colar os arquivos desta pasta.

## Passos
1. Settings / Conversation AI / AI Employees → Create Agent
2. Nome: **Assistente Gamma Vet** (ou nome de pessoa definido pela Gamma) + deixar explícito “assistente virtual”
3. Colar `prompt_momento1.md` em Bot Goals / Instructions
4. Knowledge / Training: upload ou colar:
   - `../knowledge/00_overrides_reuniao.md`
   - `../knowledge/01_procedimentos_operacionais.md`
   - `../knowledge/02_descritivos_exames.md` (se existir)
   - Conteúdo de `Procedimentos_GammaVet.md` (tabela completa)
5. Actions Momento 1 — **ON**:
   - Update contact fields
   - Add/remove tags
   - Trigger workflow (`triagem_completa`, `fora_horario`, `fora_escopo`, `handoff`)
   - Transfer / stop bot
6. Actions — **OFF**:
   - Appointment booking
   - Cancel/reschedule appointment
   - Send booking link as confirmation
7. Canal: WhatsApp (número de teste Gênesis primeiro)
8. Whitelist / WF-09 até Fase 4
9. Testar no painel de teste do bot com cenários T1–T13

## Meta do bot (texto curto para UI)
Coletar dados do responsável e do pet, preferência de período (manhã/tarde), procedimento e pedido médico; informar custos quando conhecidos; transferir para a equipe humana agendar. Não confirmar horário final.
