# Fase 3 — Roteiro de testes internos

## Pré-requisitos
- [ ] Pipeline criado na UI
- [ ] Tags + custom fields + calendários (API)
- [ ] Workflows WF-01…WF-09
- [ ] Agente Momento 1 com KB carregada
- [ ] Appointment Booking **desligado**
- [ ] Contatos importados com `teste_interno` (+ `cliente_ativo` onde couber)
- [ ] Whitelist ativa
- [ ] Nome do assistente definido pela Gamma

## Números / papéis sugeridos
Ver `../provisioning/import_clientes_ativos_modelo.csv` (substituir phones reais).

| Papel | Cenário |
|-------|---------|
| Marcelo | Ativo multi-pet + Tomo urgência |
| Mari | Novo lead US Fernanda |
| Gustavo | Cintilo renal urgência |
| Recepção | Fora do horário / aguardando |
| Marcela / Júlia | Perguntas aleatórias / fora do escopo |
| Fernanda | US + microbolhas |

## Cenários obrigatórios (DoD Momento 1)

| # | Cenário | Resultado esperado |
|---|---------|-------------------|
| T1 | Cliente ativo multi-pet | Saudação com nome + pergunta qual pet |
| T2 | Novo lead | Saudação genérica + coleta |
| T3 | Tomografia | Urgência + notificação + fila Tomografia; IA **não** confirma slot |
| T4 | Cintilo renal | Urgência + sinal/PIX informados |
| T5 | Cintilo tireoide felina | Valor R$ 1.750 |
| T6 | Ressonância | Exames não atendidos + lista de exames |
| T7 | Fora do horário | Tag aguardando + mensagem retorno |
| T8 | PDF pedido | Handoff humano |
| T9 | Foto/print pedido | Segue triagem / tag recebido |
| T10 | US Fernanda/Luciana | Preferência Fernanda citada |
| T11 | Follow-up | Até 5 toques nos intervalos; respeita janela |
| T12 | Valor vazio (endoscopia) | “Equipe confirma” — não inventa |
| T13 | Pedido de agendamento direto | Explica que equipe confirma horário |

## Ciclo
1. Executar cenários  
2. Registrar falhas em `test_log.md`  
3. Corrigir prompt/WF/KB  
4. Retestar  
5. Liberar saudação/coleta (soft) só após T1–T13 OK  

## Critério de saída Fase 3
Todos os cenários T1–T13 passam 2 vezes consecutivas com testadores diferentes.
