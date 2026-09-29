# Pello Menos — automação GHL

Scripts, exports e viewer de conversas da **Pello Menos** (Franchising e subcontas).

- Credenciais: `.env` na raiz do repositório (`GHL_PELLO_*`, `GHL_AGENCY_*` quando aplicável).
- **Export conversas Flamengo (FLA):** `python export_fla_conversas_franchising.py`
- **Viewer estilo chat (com filtros):** `exports\fla-conversas\viewer\abrir.bat`
- Export **sem telefone** do cliente; inclui tags e origem (Cliente / Humano / Automação / Sistema).

Saídas ficam em `exports/`.
