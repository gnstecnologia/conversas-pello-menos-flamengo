# Multiodonto — entendimento consolidado

## Conta
- Clínica Multiodonto Odontologia
- Location: 3R4hY0j3TJyj2SkmSQL3
- Unidades: Campo Grande + Barra da Tijuca

## IA
- Agent primário: Letícia IA Agendamento (3Fzfmx7ViwyD9v16h4DR) — auto-pilot
- Bot teste (secundário)
- KB: Base de Conhecimento - Multiodonto V1.0 (HjJZbTH2w5riiz6GeC5y) — 1 URL (doc Google JUN/2026)
- Escopo: SÓ clínico geral (consulta/limpeza/avaliação/odonto ped 5+)
- Fora do escopo → telefone da unidade (não agenda pela IA)

### Nunca agenda pela IA
Carlos Augusto (orto), Leonardo (orto), Pedro Cardoso (só telefone). Só dentistas do mapa do dia.

### Fluxo Letícia
Saudação → dados (1ª vez) → unidade → especialidade → convênio (bloqueante, antes da agenda) → data → filtrar profissionais do DIA → slots reais → revisão → booking sistema

### Convênios bloqueados
APPAI/Appai (nunca marcar, nem para hoje), Unimed, Sempre Odonto, Assist, Odonto Life, MetLife, Bradesco Dental, OdontoPrev, Dental Uni

### Canal / endodontia
Somente particular. Nenhum convênio. Agendamento só por telefone (nunca pela IA).

### Valores particular (só consulta)
CG: clínico R$100 | estomatologia R$400 | aval. orto R$50
Barra: clínico R$250 | estomatologia R$600 | aval. orto R$80
Procedimentos: nunca informar valor

### Actions
updateContactField (nome, idade, DN, CPF, CPF resp, endereço, telefone, unidade, especialidade, procedimento, convênio, carteirinha)
appointmentBooking
advancedFollowup (parou de responder)

## Calendários oficiais IA (service_booking 30 min)

### Campo Grande
| Profissional | Dias | Horários |
|---|---|---|
| Dr Lucas Scherres | Ter, Sex, Sáb | Ter/Sex 09-13 e 14-19; Sáb 09-13:30 |
| Dr Lucas Castro | Qua, Qui, Sáb | Qua/Qui 09-12 e 13-19; Sáb 09-13:30 |
| Dra Thais Campos | Sex, Sáb | Sex 09-12 e 13-19; Sáb 09-13:30 |
| Dra Giovanna Ferreira | Seg, Qui | 09-12 e 13-19 |
| Dr Rafael Ramos | Seg, Qua | 09-13 e 14-19 |

### Barra da Tijuca
| Profissional | Dias | Horários |
|---|---|---|
| Dra Juliana Cardoso | Seg–Qui | Seg/Qua 11-13 e 14-18; Ter/Qui 09-13 e 14-17 |
| Dra Giovanna Ferreira | Sáb | 09-13 |
| Dr Rafael Ramos | Sáb | 09-13 |

### Existem mas IA NÃO usa
- Carlos Augusto CG/Barra (orto)
- Leonardo CG (orto)
- Personal calendars da equipe

## Telefones
CG: (21) 3161-2205 | 99594-2638
Barra: (21) 2442-5192 | 95904-2251

## Endereços
CG: R. Cel. Agostinho, 76 - Sala 401
Barra: Av. das Américas, 4790 - Sala 303, Barra Shopping

## Pipeline Agendamento
Novo Lead → Triagem → Profissional e Horário → Agendado → Compareceu / Reagendar / Cancelado

## Workflow publicado relevante
Acionamento IA (published). Maioria dos outros em draft.