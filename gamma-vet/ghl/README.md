# Implementação GHL — Gamma Vet

Location: `MhplIQf1baCvRBNGPTOj`  
Agente criado: **Assistente Gamma Vet** (`nEndeX5NE4uDJG7414RF`) — mode `off` até testes.

## Status por fase

| Fase | Status | O que foi entregue |
|------|--------|-------------------|
| 0 Fundação | Parcial na API + checklist UI | Tags, fields, calendários, CSV, pipeline spec, checklist usuários |
| 1 Agente | Agente + prompt + WF specs | Agent API criado; KB arquivos; workflows documentados (criar na UI) |
| 2 Conteúdo | Entregue (provisório) | Fluxos por setor + sinal/taxa + preços KB |
| 3 Testes | Roteiro pronto | `testing/roteiro_testes.md` — executar com números reais |
| 4 Soft launch | Checklist pronto | `launch/fase4_soft_launch.md` |
| 5 Canais | Checklist pronto | `launch/fase5_canais.md` (bloquear até aprovação) |
| 6 Momento 2 | Checklist pronto | `launch/fase6_momento2.md` |

## Pendências manuais na UI (obrigatórias)
1. Criar pipeline **Agendamento Gamma Vet** (13 estágios) — API não cria pipeline.
2. Criar workflows WF-01…WF-09 conforme `workflows/README_workflows.md`.
3. Anexar knowledge files no painel do agente + ligar actions (fields/tags/trigger/transfer).
4. Ajustar openHours dos calendários.
5. Convidar usuários / permissões.
6. Importar CSV com telefones reais + whitelist.
7. Definir nome de pessoa do assistente e atualizar prompt.
8. Só então ligar `mode` do agente e WhatsApp de teste.

## Pastas
- `provisioning/` — tags/fields/calendars results, CSV, pipeline
- `agent/` — prompt, setup UI, agent_created.json
- `knowledge/` — overrides reunião + procedimentos
- `workflows/` — especificação dos 9 WFs
- `content/` — fluxos setor + follow-ups
- `testing/` — roteiro DoD
- `launch/` — fases 4–6
