# Fase 0 — Checklist UI (itens não cobertos pela API)

## Já provisionado via API (location MhplIQf1baCvRBNGPTOj)
- [x] 12 tags do plano
- [x] 33 custom fields (contato + pets 1–3)
- [x] 10 calendários de serviço (US Fernanda/Luciana, Eco, ECG, RX, Tomo, Endo, Cintilo, Radioiodo, Pré-reserva)
- [x] CSV modelo de importação de ativos/teste
- [x] Spec do pipeline em `pipeline_stages.json`

## Criar manualmente na UI GHL

### 1. Pipeline `Agendamento Gamma Vet`
Opportunities → Pipelines → Create. Estágios na ordem de `pipeline_stages.json` (13 estágios).

### 2. Usuários / permissões
Antes de e-mail de senha, enviar no grupo Marcelo + Mari:
| Nome | Permissão sugerida | Escopo |
|------|-------------------|--------|
| Marcelo | Admin / Manager | Full |
| Mari | User + Conversations + Opportunities | Atendimento + funil |
| Recepção | User + Conversations + Calendars | Agenda + inbox |
| Dra. Fernanda | User + Calendars (US) | Agenda US |
| Dra. Luciana | User + Calendars (US) | Agenda US |

Depois: Settings → My Staff → invite / reset password emails.

### 3. Importar contatos de teste
Contacts → Import → `import_clientes_ativos_modelo.csv` (trocar phones pelos reais). Garantir tags `teste_interno` e `cliente_ativo`.

### 4. Custom Object Pet (opcional / recomendado depois)
Settings → Custom Objects → Pet ligado a Contact. Enquanto isso, usar Pet 1/2/3 fields.

### 5. Horários dos calendários
Calendários foram criados sem openHours detalhados (limitação do payload). Ajustar na UI os horários por serviço conforme Procedimentos.
