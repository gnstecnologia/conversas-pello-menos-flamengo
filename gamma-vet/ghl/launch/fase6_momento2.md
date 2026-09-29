# Fase 6 — Momento 2 (pós-estabilidade)

## Ativar Appointment Booking (gradual)
1. Começar com **US** (Fernanda + Luciana) e **Tomografia**
2. Medicina nuclear por último (mais complexa)
3. Calendário **Pré-reserva Interna**: bot agenda ali com `autoConfirm=false` / status pendente
4. Cliente **não** recebe “você está marcado”; recebe “pré-reserva; equipe confirma”
5. WF pós-booking: notificar humano + stage Profissional e horário / Em atendimento

## OCR pedido médico
- Imagem: habilitar leitura no agente
- PDF: webhook → OCR externo (opcional) → custom field; senão handoff

## Sinal em Tomografia
- Decisão de **negócio** (Marcelo citou cancelamentos)
- Se aprovado: atualizar KB + campos sinal + mensagem IA

## Checklist técnico Momento 2
- [ ] Multi-calendar no bot com descriptions/keywords
- [ ] Fallback calendar
- [ ] Cancel/reschedule bot: decidir política (recomendado OFF no início do Momento 2)
- [ ] Testes US/TC com pré-reserva
- [ ] Só então expandir cintilos
