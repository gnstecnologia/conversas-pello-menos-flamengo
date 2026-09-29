# -*- coding: utf-8 -*-
"""Gera o PDF de controle financeiro Pello Menos / GHL / WhatsApp."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

OUT = Path(r"c:\Users\GC1\Desktop\Automação GHL\Pello-Menos-Controle-Financeiro-GHL.pdf")

pdfmetrics.registerFont(TTFont("Arial", r"C:\Windows\Fonts\arial.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Bold", r"C:\Windows\Fonts\arialbd.ttf"))

NAVY = colors.HexColor("#0F2C4C")
TEAL = colors.HexColor("#0E6B6B")
GOLD = colors.HexColor("#C4A35A")
RED = colors.HexColor("#9B2C2C")
AMBER = colors.HexColor("#8A5A00")
BG = colors.HexColor("#F4F1EA")
CARD = colors.HexColor("#FFFFFF")
LINE = colors.HexColor("#D6D0C4")
SOFT = colors.HexColor("#E8F3F3")
WARN = colors.HexColor("#FFF4E0")
DANGER = colors.HexColor("#F8E6E6")
OK = colors.HexColor("#E5F4EA")
MUTED = colors.HexColor("#5C6670")


def styles():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle(name="CoverKicker", fontName="Arial", fontSize=9, textColor=GOLD, tracking=1.2, spaceAfter=6))
    s.add(ParagraphStyle(name="CoverTitle", fontName="Arial-Bold", fontSize=22, textColor=NAVY, leading=28, spaceAfter=8))
    s.add(ParagraphStyle(name="CoverSub", fontName="Arial", fontSize=11, textColor=MUTED, leading=16, spaceAfter=4))
    s.add(ParagraphStyle(name="H1", fontName="Arial-Bold", fontSize=14, textColor=NAVY, spaceBefore=14, spaceAfter=8, leading=18))
    s.add(ParagraphStyle(name="H2", fontName="Arial-Bold", fontSize=11.5, textColor=TEAL, spaceBefore=10, spaceAfter=6, leading=15))
    s.add(ParagraphStyle(name="Body", fontName="Arial", fontSize=9.5, textColor=NAVY, leading=14, alignment=TA_JUSTIFY, spaceAfter=6))
    s.add(ParagraphStyle(name="BodyLeft", fontName="Arial", fontSize=9.5, textColor=NAVY, leading=14, alignment=TA_LEFT, spaceAfter=6))
    s.add(ParagraphStyle(name="Small", fontName="Arial", fontSize=8.2, textColor=MUTED, leading=12, spaceAfter=3))
    s.add(ParagraphStyle(name="Cell", fontName="Arial", fontSize=8.2, textColor=NAVY, leading=11))
    s.add(ParagraphStyle(name="CellB", fontName="Arial-Bold", fontSize=8.2, textColor=NAVY, leading=11))
    s.add(ParagraphStyle(name="Th", fontName="Arial-Bold", fontSize=8, textColor=colors.white, leading=11))
    s.add(ParagraphStyle(name="Box", fontName="Arial", fontSize=9, textColor=NAVY, leading=13, alignment=TA_LEFT))
    s.add(ParagraphStyle(name="BoxB", fontName="Arial-Bold", fontSize=9, textColor=NAVY, leading=13))
    s.add(ParagraphStyle(name="Footer", fontName="Arial", fontSize=8, textColor=MUTED, alignment=TA_CENTER))
    s.add(ParagraphStyle(name="BulletBody", fontName="Arial", fontSize=9.4, textColor=NAVY, leading=13.5))
    return s


S = styles()


def p(text, style="Body"):
    return Paragraph(text, S[style])


def box(title, body, bg=SOFT, border=TEAL):
    data = [[p(f"<b>{title}</b>", "BoxB")], [p(body, "Box")]]
    t = Table(data, colWidths=[17.4 * cm])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), bg),
                ("BOX", (0, 0), (-1, -1), 0.8, border),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (0, 0), 8),
                ("BOTTOMPADDING", (0, -1), (-1, -1), 8),
                ("TOPPADDING", (0, 1), (-1, 1), 2),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return KeepTogether([t, Spacer(1, 8)])


def table(headers, rows, widths=None):
    head = [p(h, "Th") for h in headers]
    body = []
    for r in rows:
        body.append([p(c, "CellB") if i == 0 else p(c, "Cell") for i, c in enumerate(r)])
    data = [head] + body
    t = Table(data, colWidths=widths, repeatRows=1)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Arial-Bold"),
        ("BACKGROUND", (0, 1), (-1, -1), CARD),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [CARD, colors.HexColor("#F7F5F0")]),
        ("GRID", (0, 0), (-1, -1), 0.3, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    t.setStyle(TableStyle(style_cmds))
    return t


def bullets(items):
    return ListFlowable(
        [ListItem(p(i, "BulletBody"), leftIndent=8, bulletColor=TEAL) for i in items],
        bulletType="bullet",
        start="•",
        leftIndent=12,
        bulletFontName="Arial",
        bulletFontSize=9,
        spaceBefore=2,
        spaceAfter=8,
    )


def header_footer(canvas, doc):
    canvas.saveState()
    w, h = A4
    canvas.setFillColor(NAVY)
    canvas.rect(0, h - 14, w, 14, fill=1, stroke=0)
    canvas.setFillColor(GOLD)
    canvas.rect(0, h - 16, w, 2.2, fill=1, stroke=0)
    canvas.setFillColor(NAVY)
    canvas.rect(0, 0, w, 22, fill=1, stroke=0)
    canvas.setFillColor(GOLD)
    canvas.rect(0, 22, w, 2, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("Arial", 7.5)
    canvas.drawString(18 * mm, h - 10, "PELLO MENOS  ·  GSales / Genesis  ·  Confidencial operacional")
    canvas.drawRightString(w - 18 * mm, h - 10, "Controle financeiro GHL + WhatsApp")
    canvas.drawString(18 * mm, 8, "Não compartilhar senhas, PIT ou cartões neste arquivo.")
    canvas.drawRightString(w - 18 * mm, 8, f"Pág. {doc.page}")
    canvas.restoreState()


def cover_header_footer(canvas, doc):
    canvas.saveState()
    w, h = A4
    canvas.setFillColor(NAVY)
    canvas.rect(0, 0, w, h, fill=1, stroke=0)
    canvas.setFillColor(TEAL)
    canvas.rect(0, 0, 18, h, fill=1, stroke=0)
    canvas.setFillColor(GOLD)
    canvas.rect(18, 0, 4, h, fill=1, stroke=0)
    canvas.restoreState()


def build():
    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=A4,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.4 * cm,
        title="Pello Menos — Controle financeiro GHL e WhatsApp",
        author="Genesis / GSales",
        subject="Manutenção de planos SaaS, rebilling e disparos WhatsApp",
    )
    story = []

    # ----- CAPA (flow sobre fundo escuro: usamos primeira página especial) -----
    story.append(Spacer(1, 4.2 * cm))
    story.append(Paragraph("MANUAL OPERACIONAL", ParagraphStyle("ck", fontName="Arial", fontSize=10, textColor=GOLD, tracking=1.4)))
    story.append(Spacer(1, 10))
    story.append(Paragraph("Pello Menos", ParagraphStyle("ct", fontName="Arial-Bold", fontSize=28, textColor=colors.white, leading=34)))
    story.append(Paragraph("Controle financeiro no GoHighLevel", ParagraphStyle("ct2", fontName="Arial-Bold", fontSize=16, textColor=colors.HexColor("#B7E0DC"), leading=22, spaceBefore=4)))
    story.append(Spacer(1, 16))
    story.append(Paragraph(
        "Planos SaaS · taxa da Franqueadora · taxa mínima das lojas ·<br/>mensalidade WhatsApp oficial · disparo (template de marketing) · manutenção mensal",
        ParagraphStyle("cs", fontName="Arial", fontSize=10.5, textColor=colors.HexColor("#D5DDE6"), leading=16),
    ))
    story.append(Spacer(1, 36))
    meta = [
        ["Conta matriz", "FRANQUIA | PELLO MENOS"],
        ["Lojas ativas", "URG  ·  LBI  ·  LMA  (3 × US$ 15 = US$ 45)"],
        ["Agência", "Gsales CRM  (Genesis paga o WhatsApp oficial ao GHL)"],
        ["Vigência", date.today().strftime("%d/%m/%Y")],
        ["Regra de ouro", "Mensal na Franqueadora. Disparo em cada loja."],
    ]
    mt = Table([[Paragraph(f"<font color='#C4A35A'><b>{a}</b></font>", S["Small"]), Paragraph(f"<font color='white'>{b}</font>", S["Small"])] for a, b in meta], colWidths=[4.2 * cm, 12 * cm])
    mt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#17385C")),
        ("BOX", (0, 0), (-1, -1), 0.4, GOLD),
        ("INNERGRID", (0, 0), (-1, -1), 0.2, colors.HexColor("#2A5278")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(mt)
    story.append(PageBreak())

    # ----- 1 -----
    story.append(p("1. Para que serve este manual", "H1"))
    story.append(p(
        "Este documento é o controle financeiro da operação Pello Menos no GoHighLevel. "
        "Ele separa o que a <b>Franqueadora</b> paga, o que <b>cada loja</b> paga e o que a "
        "<b>Genesis (agência Gsales)</b> paga ao GHL. Use na manutenção mensal, na entrada de "
        "novo franqueado e antes de qualquer disparo de WhatsApp."
    ))
    story.append(box(
        "Regra de ouro — nunca misturar",
        "Há <b>dois dinheiros</b> e eles não podem cair no mesmo lugar.<br/>"
        "1) <b>Mensalidade / taxa</b> → cartão da <b>FRANQUIA | PELLO MENOS</b> (hoje US$ 45 = 3 lojas × US$ 15).<br/>"
        "2) <b>Disparo WhatsApp</b> (template de marketing aprovado) → cartão/wallet da <b>loja que disparou</b> (URG, LBI ou LMA).<br/><br/>"
        "A taxa de <b>US$ 1</b> em cada loja é só a “trava” para existir cobrança e cartão na unidade. "
        "Não é o WhatsApp. Não é a taxa de US$ 15.",
        SOFT,
        TEAL,
    ))

    # ----- 2 -----
    story.append(p("2. Quem é quem", "H1"))
    story.append(table(
        ["Papel", "Conta no GHL", "Paga", "Não paga"],
        [
            [
                "Franqueadora",
                "FRANQUIA | PELLO MENOS<br/>R. Marcílio Dias, 620 — Praia Grande/SP",
                "Plano SaaS de <b>US$ 45/mês</b> (US$ 15 × 3 lojas). Editar na mão quando entrar/sair loja.",
                "Disparo das lojas. WhatsApp oficial de US$ 10 (isso é da Genesis).",
            ],
            [
                "Loja URG",
                "Pello Menos - URG<br/>Usuário: snp@pellomenos.com.br",
                "Plano <b>US$ 1</b> + <b>todo disparo</b> feito nesta conta.",
                "Os US$ 15 da taxa da rede. Mensalidade WhatsApp de US$ 15 (fica sem upsell).",
            ],
            [
                "Loja LBI",
                "Pello Menos - LBI<br/>Usuário: lbi@pellomenos.com.br",
                "Plano <b>US$ 1</b> + disparos desta conta.",
                "Idem.",
            ],
            [
                "Loja LMA",
                "Pello Menos - LMA<br/>Usuário: comercial1@pellomenos.com.br",
                "Plano <b>US$ 1</b> + disparos desta conta.",
                "Idem.",
            ],
            [
                "Agência Genesis",
                "Gsales CRM",
                "WhatsApp oficial ao GHL: <b>US$ 10 por loja com número ligado</b> (3 lojas = US$ 30). Wallet de uso se o rebilling da loja falhar.",
                "Não deve comer disparo se o cartão da loja estiver ok.",
            ],
        ],
        [3.0 * cm, 4.6 * cm, 5.0 * cm, 4.8 * cm],
    ))
    story.append(Spacer(1, 6))
    story.append(p(
        "Contas que <b>não</b> entram neste desenho: Pello Menos | Franchising (hub de anúncio), "
        "Pello Menos | Franqueadora antiga, e a Uruguai antiga. Não colocar plano de 45 nem rebilling de disparo lá.",
        "Small",
    ))

    # ----- 3 -----
    story.append(p("3. Os dois planos SaaS", "H1"))
    story.append(p(
        "No SaaS Configurator existem dois produtos. Cada um vive em um tipo de conta. "
        "O GHL cobra o valor do plano no <b>cartão da subconta inscrita</b>. Ele <b>não</b> multiplica sozinho 15 × N lojas."
    ))
    story.append(table(
        ["Plano", "Preço", "Onde aplicar", "Para que serve", "O que NÃO faz"],
        [
            [
                "Pello Menos Planos Dollar<br/>(taxa rede)",
                "US$ 45 / mês<br/>US$ 540 / ano",
                "Só <b>FRANQUIA | PELLO MENOS</b>",
                "Cobrar a Franqueadora pelos US$ 15 de cada loja ativa. Com 3 lojas: 15×3=45. Com 4: editar para 60.",
                "Não paga a Meta. Não paga o disparo. Não sobe sozinho quando entra franqueado.",
            ],
            [
                "Pello Menos | Lojas<br/>(taxa mínima)",
                "US$ 1 / mês<br/>US$ 10 / ano",
                "Cada loja: URG, LBI, LMA e as próximas",
                "Taxa mínima + obriga cartão na unidade. Sem cartão, o disparo não tem de onde sair e volta para a Genesis.",
                "Não é o WhatsApp de US$ 10/15. Não substitui os 45 da Franqueadora.",
            ],
        ],
        [3.4 * cm, 2.8 * cm, 3.4 * cm, 4.2 * cm, 3.6 * cm],
    ))
    story.append(Spacer(1, 8))
    story.append(box(
        "Atenção — trial de 30 dias",
        "Os dois planos estão com <b>30 days trial</b>. Enquanto o trial não acabar, <b>não cai nem os 45 nem o 1</b>. "
        "Se a regra for cobrar no ato: trial = <b>0 dias</b> nos dois planos. Créditos cortesia: US$ 0 (já está certo).",
        WARN,
        GOLD,
    ))

    # ----- 4 -----
    story.append(p("4. WhatsApp: três cobranças diferentes", "H1"))
    story.append(p("É o ponto que mais confunde. São <b>três</b> linhas. Se misturar, a Genesis paga tudo ou a loja paga duas vezes."))
    story.append(table(
        ["#", "O quê", "Tela no GHL", "Quem deveria pagar", "Configuração correta"],
        [
            [
                "A",
                "<b>Oficial GHL</b><br/>US$ 10 / número / mês",
                "Custo interno da agência (Add-ons / WhatsApp)",
                "<b>Genesis</b> → GHL. Sempre. Não tem como mandar isso para a Franqueadora direto.",
                "Não marcar addon WhatsApp US$ 10 dentro do plano de 45 nem do de 1. O 45 já existe para a Franqueadora te reembolsar esses 10 + margem.",
            ],
            [
                "B",
                "<b>Revenda mensal</b><br/>loja US$ 15 / Genesis US$ 10 / lucro US$ 5",
                "Reselling WhatsApp da subconta",
                "No nosso modelo: <b>ninguém na loja</b>. A Franqueadora já pagou via plano de 45.",
                "Nas 3 lojas: <b>Deployed without upsell</b>. Se ligar o upsell de 15 na loja, ela paga 15 <b>e</b> a Franqueadora também — cobra duas vezes.",
            ],
            [
                "C",
                "<b>Disparo / uso</b><br/>template marketing entregue",
                "Rebilling WhatsApp (usage)",
                "<b>A loja que disparou</b>",
                "Interruptor <b>ligado</b>, markup <b>1.00×</b> (custo = custo, lucro 0 no disparo), <b>Save</b> em URG, LBI e LMA.",
            ],
        ],
        [1.2 * cm, 3.4 * cm, 3.6 * cm, 3.6 * cm, 5.6 * cm],
    ))
    story.append(Spacer(1, 8))
    story.append(p("4.1 Como o GHL movimenta o dinheiro do disparo", "H2"))
    story.append(bullets([
        "O GHL <b>sempre</b> baixa primeiro a <b>wallet da agência (Gsales / Genesis)</b>.",
        "Se o rebilling daquela loja estiver <b>ligado</b> e o cartão/wallet da loja tiver saldo, ele <b>repassa</b> o mesmo valor (1.00×) para a loja.",
        "Se o cartão da loja falhar, estiver <b>past_due</b> ou o rebilling estiver desligado → o custo <b>fica na Genesis</b>.",
        "A Meta só cobra mensagem <b>entregue</b>. Sem WhatsApp / falhou = não cobra.",
        "A tabela da tela de rebilling que mostra US$ 0,0744 é uma <b>média da UI</b>. O valor real no Brasil (marketing) é cerca de <b>US$ 0,0625</b> por entrega. Uruguai entra em “Rest of LATAM” (~US$ 0,0740). Quase todos os números atuais das 3 lojas são +55.",
    ]))

    story.append(p("4.2 Referência de custo de 1 disparo (template marketing aprovado)", "H2"))
    story.append(p(
        "Levantamento nas contas oficiais (1 envio, 1 telefone único, só entregues). Não inclui a mensalidade de US$ 10/15."
    ))
    story.append(table(
        ["Conta", "Celulares únicos", "Tarifa usada", "Custo estimado"],
        [
            ["URG", "136 (135 BR + 1 UK)", "US$ 0,0625 (BR)", "≈ US$ 8,51  ·  ≈ R$ 44"],
            ["LBI", "224 (223 BR + 1 UK)", "US$ 0,0625 (BR)", "≈ US$ 14,01  ·  ≈ R$ 72"],
            ["LMA", "Conferir antes de disparar", "Mesma regra", "Contar telefones únicos com +55"],
            ["Total URG+LBI", "360", "—", "≈ US$ 22,52  ·  ≈ R$ 116"],
        ],
        [3.2 * cm, 4.6 * cm, 4.2 * cm, 5.4 * cm],
    ))
    story.append(Spacer(1, 6))
    story.append(p(
        "Este número é <b>custo</b>, não receita. Só “volta” se a campanha gerar venda. "
        "Com rebilling 1.00×, quem paga é a loja — a Genesis não ganha no disparo (e não deve perder, se o cartão da loja passar).",
        "Small",
    ))

    # ----- 5 -----
    story.append(p("5. Fechamento mensal (3 lojas ativas)", "H1"))
    story.append(p("Quando os trials acabarem e os cartões passarem, o mês-padrão fica assim:"))
    story.append(table(
        ["Movimento", "Sai de", "Entra em", "Valor"],
        [
            ["Plano taxa rede", "Cartão Franqueadora", "Stripe da agência (Genesis)", "US$ 45"],
            ["Taxa mínima 3 lojas", "Cartão URG + LBI + LMA", "Stripe da agência", "US$ 1 + 1 + 1 = US$ 3"],
            ["WhatsApp oficial 3 números", "Wallet/cartão Genesis → GHL", "GHL / Meta (assinatura)", "US$ 30"],
            ["Resultado mensal da Genesis (sem disparo)", "—", "—", "<b>US$ 48 − 30 = + US$ 18</b>"],
            ["Disparos", "Cartão da loja que enviou", "Passa pela wallet Genesis e some (1.00×)", "Variável (ex.: URG ≈ 8,51)"],
        ],
        [4.6 * cm, 4.4 * cm, 5.0 * cm, 3.4 * cm],
    ))
    story.append(Spacer(1, 8))
    story.append(box(
        "Conferência rápida do mês",
        "Genesis deve ver no Stripe: <b>45 + 3 = 48</b>.<br/>"
        "Genesis deve ver no billing GHL: <b>10 × quantidade de WhatsApp ligados</b>.<br/>"
        "Cada loja deve ver: <b>US$ 1</b> + linhas de uso WhatsApp do que ela disparou.<br/>"
        "Franqueadora deve ver: <b>só os 45</b> (ou o novo valor, se você editou). Nada de template.<br/>"
        "Se a wallet da Genesis baixar e a loja não tiver débito equivalente → rebilling falhou. Parar disparo e olhar cartão da loja.",
        OK,
        TEAL,
    ))

    # ----- 6 -----
    story.append(p("6. Status ao fechar este manual — o que ainda não cobra", "H1"))
    story.append(table(
        ["Conta", "Plano", "Status visto na API", "Risco"],
        [
            ["FRANQUIA | PELLO MENOS", "US$ 45", "<b>past_due</b>", "Cartão da Matriz não passou. Os 45 não estão caindo. Prioridade 1."],
            ["URG", "US$ 1", "<b>trialing</b>", "30 dias grátis. Taxa 1 ainda não cai."],
            ["LBI", "US$ 1", "<b>past_due</b>", "Cartão da loja falhou. Disparo desta conta tende a voltar para a Genesis."],
            ["LMA", "US$ 1", "<b>trialing</b>", "30 dias grátis. Conferir cartão antes do 1º disparo."],
        ],
        [4.2 * cm, 2.4 * cm, 3.0 * cm, 7.8 * cm],
    ))
    story.append(Spacer(1, 8))
    story.append(box(
        "Não disparar em massa enquanto isto estiver vermelho",
        "LBI <b>past_due</b> + Franqueadora <b>past_due</b> = o modelo financeiro ainda não está em pé. "
        "O GHL deixa enviar. Quem paga, nesse caso, é a Genesis.",
        DANGER,
        RED,
    ))

    # ----- 7 -----
    story.append(p("7. Manutenção — o que vigiar todo mês", "H1"))
    story.append(p("7.1 Checklist mensal (financeiro)", "H2"))
    story.append(table(
        ["#", "Checagem", "Onde", "Sinal de problema"],
        [
            ["1", "Plano da Franqueadora = US$ 15 × lojas ativas com WhatsApp", "SaaS da FRANQUIA | PELLO MENOS", "Continua 45 com 4 lojas, ou 45 com 2 lojas."],
            ["2", "Assinatura da Franqueadora = active (não past_due / unpaid)", "SaaS / Company Billing da matriz", "past_due, On Hold, Pending Payment."],
            ["3", "Cada loja no plano de US$ 1, status active", "SaaS de URG, LBI, LMA", "Loja sem plano, trial eterno, ou no plano de 45."],
            ["4", "Cartão válido em cada loja (saldo/limite)", "Billing da loja", "Falha de cobrança, wallet zerada."],
            ["5", "Rebilling WhatsApp ON e 1.00× nas 3 lojas", "Manage Client → WhatsApp usage", "Toggle off = Genesis come o disparo."],
            ["6", "Reselling da loja = without upsell (sem US$ 15 na loja)", "Tela WhatsApp Reselling da loja", "Customer pay 15 ligado = cobra duas vezes."],
            ["7", "Quantos números oficiais estão ligados = N; Genesis pagou 10×N", "Agency Billing / Add-ons", "4 números ligados e plano da matriz ainda em 45."],
            ["8", "Uso WhatsApp do mês bate com disparos da loja", "Wallet agência vs billing da loja", "Uso na wallet Genesis sem espelho na loja."],
            ["9", "Nenhuma loja com dono vazio em Contatos/Oportunidades", "Contatos + Opportunities", "Usuário da loja (snp / lbi / comercial1) não vê o lead."],
        ],
        [1.1 * cm, 5.8 * cm, 4.8 * cm, 5.7 * cm],
    ))

    story.append(p("7.2 Quando entra um franqueado novo", "H2"))
    story.append(bullets([
        "Criar/clonar a <b>subconta da loja</b> (não usar a FRANQUIA | PELLO MENOS como loja).",
        "Colocar a loja no plano <b>Pello Menos | Lojas — US$ 1</b>. Trial 0 se for cobrar já. Cadastrar <b>cartão da unidade</b>.",
        "Na Franqueadora: editar o plano de 45 para <b>15 × novo total</b> (4 lojas = 60; 5 = 75). Só essa conta.",
        "Ligar WhatsApp na loja em <b>Direct Deploy / without upsell</b>. Não vender o addon de 15 para ela.",
        "Ligar rebilling de uso <b>ON + 1.00× + Save</b> nessa loja.",
        "Criar o usuário padrão da loja (e-mail da sigla, senha @Genesis12345 + SIGLA), só dados atribuídos.",
        "Atribuir todos os contatos e oportunidades dessa conta ao usuário da loja.",
        "Anotar no controle: nome da loja, location ID, data, N lojas, valor do plano da matriz.",
    ]))

    story.append(p("7.3 Quando uma loja sai ou pausa o WhatsApp", "H2"))
    story.append(bullets([
        "Desligar o número oficial dessa loja (senão a Genesis continua pagando US$ 10).",
        "Baixar o plano da Franqueadora (3 lojas → 45; 2 → 30).",
        "Decidir se o plano de US$ 1 da loja permanece (conta aberta) ou se a assinatura é cancelada.",
        "Não deixar rebilling ligado numa conta sem cartão “por precaução” — ou a wallet da Genesis come o restante.",
    ]))

    story.append(p("7.4 Antes de qualquer disparo de template", "H2"))
    story.append(bullets([
        "Template de <b>marketing aprovado</b> na WABA daquela loja (não usar a WABA de outra conta).",
        "Rebilling ON 1.00× <b>nessa</b> loja.",
        "Cartão/wallet da loja com folga (custo ≈ 0,0625 × quantidade de celulares únicos).",
        "Contar telefones únicos com DDI. Quase tudo é +55. Número sem WhatsApp não deveria ser disparado.",
        "Disparar <b>de dentro da conta da loja</b>, não da Franqueadora nem do Franchising.",
        "1 envio = 1 cobrança por entrega. Reenviar a base = pagar de novo.",
    ]))

    # ----- 8 -----
    story.append(p("8. O que nunca fazer", "H1"))
    story.append(table(
        ["Erro", "O que acontece"],
        [
            ["Colocar o plano de US$ 45 numa loja", "A loja paga a taxa da rede inteira. A Franqueadora deixa de ser o pagador único."],
            ["Colocar o plano de US$ 1 na Franqueadora", "A matriz não paga os 15×N. A Genesis fica só com o custo do WhatsApp (US$ 10×N)."],
            ["Ligar upsell de US$ 15 na loja e manter os 45 na matriz", "Mensalidade em dobro. Franqueado reclama com razão."],
            ["Marcar addon WhatsApp US$ 10 dentro do plano SaaS", "GHL cobra US$ 10 da Genesis <b>por assinante daquele plano</b>, em cima do que já se paga por número."],
            ["Deixar rebilling desligado e disparar", "Genesis paga o template. Loja não vê a conta."],
            ["Disparar da conta Franchising / Franqueadora / Uruguai antiga", "Custa na conta errada; leads e WABA errados."],
            ["Esquecer de atribuir o dono (snp / lbi / comercial1)", "O usuário da loja não vê Contatos nem Leads (permissão: só atribuídos)."],
            ["Subir o plano da matriz sem ligar WhatsApp da loja nova (ou o contrário)", "Ou a Franqueadora paga 15 a mais sem número, ou a Genesis paga 10 sem receber 15."],
            ["Editar o preço do plano de 45 se alguma loja estiver inscrita nele", "A loja passaria a pagar 45/60. Por isso o 45 é exclusivo da FRANQUIA | PELLO MENOS."],
        ],
        [6.4 * cm, 11.0 * cm],
    ))

    # ----- 9 -----
    story.append(p("9. Onde clicar no GHL", "H1"))
    story.append(table(
        ["Tarefa", "Caminho"],
        [
            ["Ver / editar o valor 45 → 60", "Agency → SaaS Configurator → plano da Franqueadora (Pello Menos Planos Dollar). Depois confirmar a assinatura em FRANQUIA | PELLO MENOS → SaaS / Billing."],
            ["Ver se a matriz está past_due", "Entrar em FRANQUIA | PELLO MENOS → Company Billing / SaaS. Precisa do cartão da Matriz Pello, não do cartão Genesis."],
            ["Plano de US$ 1 da loja", "Sub-Account da loja → SaaS. Plano: Pello Menos | Lojas."],
            ["Rebilling do disparo", "Agency → Sub-Accounts → ⋮ da loja → Manage Client → WhatsApp (usage / markup). Toggle ON, 1.00×, Save."],
            ["Reselling mensal do número", "Mesma área da loja, bloco WhatsApp subscription. Deve permanecer <b>Deployed without upsell</b>."],
            ["Wallet da Genesis", "Agency → Billing / Wallet. Aqui o GHL tira o uso primeiro. Tem que ter lastro; o rebilling devolve."],
            ["Dono dos leads", "Dentro da loja: Contacts e Opportunities → assigned to o usuário daquela sigla."],
        ],
        [5.2 * cm, 12.2 * cm],
    ))

    # ----- 10 -----
    story.append(p("10. IDs de referência (operação)", "H1"))
    story.append(p("Úteis para suporte e para não confundir contas. Não são senha nem token.", "Small"))
    story.append(table(
        ["Conta", "Location ID", "Plano observado", "Usuário da loja"],
        [
            ["FRANQUIA | PELLO MENOS", "soAlnK8Q4F5NJE9c9X9K", "US$ 45 (editar com N lojas)", "— (cartão da Matriz)"],
            ["Pello Menos - URG", "1a0o7zlmuX4HVazkqcFV", "US$ 1  ·  loja", "snp@pellomenos.com.br"],
            ["Pello Menos - LBI", "iWMsfmAtJU97tEvl6TbI", "US$ 1  ·  loja", "lbi@pellomenos.com.br"],
            ["Pello Menos - LMA", "JSsmufl0VhKVinzGUswq", "US$ 1  ·  loja", "comercial1@pellomenos.com.br"],
            ["Agência Gsales", "company PIK3OmRl8Y7U0cy1tHSR", "Paga US$ 10 × N ao GHL", "—"],
        ],
        [4.6 * cm, 4.6 * cm, 4.2 * cm, 4.0 * cm],
    ))
    story.append(Spacer(1, 8))
    story.append(p(
        "Fora deste desenho: Franchising <font face='Arial'>wi4al7UGFzPEEJxK3xJg</font> · "
        "Franqueadora antiga <font face='Arial'>FiFGh1iuajPhozsR5FNV</font> · "
        "Uruguai antiga <font face='Arial'>xXSw3xjZQTFUqIEI3VSR</font>.",
        "Small",
    ))

    # ----- 11 -----
    story.append(p("11. Folha de controle (imprimir / copiar no mês)", "H1"))
    story.append(p("Preencher na virada do mês. N = lojas com WhatsApp oficial ligado.", "Small"))
    story.append(table(
        ["Campo", "Fórmula / o que anotar", "Este mês"],
        [
            ["Data do fechamento", "Último dia útil", ""],
            ["N lojas ativas (WA ligado)", "URG / LBI / LMA / novas", "3"],
            ["Plano Franqueadora deveria ser", "N × 15", "45"],
            ["Plano Franqueadora cobrado de fato", "Fatura Stripe/SaaS da matriz", ""],
            ["Taxa US$ 1 × lojas cobrada", "N × 1", ""],
            ["Genesis pagou ao GHL (WA oficial)", "N × 10", ""],
            ["Uso WA URG (US$)", "Billing da loja URG", ""],
            ["Uso WA LBI (US$)", "Billing da loja LBI", ""],
            ["Uso WA LMA (US$)", "Billing da loja LMA", ""],
            ["Uso na wallet Genesis", "Tem que ≈ soma das 3 lojas", ""],
            ["Diferença Genesis vs lojas", "Se &gt; 0, rebilling falhou", ""],
            ["Resultado Genesis no mês", "(45 ou N×15) + (N×1) − (N×10)", "meta: +18 com N=3"],
            ["past_due / trial em aberto?", "Listar contas", ""],
            ["Novo franqueado no mês?", "Nome + data + novo valor da matriz", ""],
        ],
        [5.2 * cm, 6.6 * cm, 5.6 * cm],
    ))
    story.append(Spacer(1, 10))
    story.append(box(
        "Resumo em uma frase",
        "A <b>Franqueadora</b> paga a taxa da rede (hoje 45). A <b>loja</b> paga US$ 1 + o que disparar. "
        "A <b>Genesis</b> paga US$ 10 por número ao GHL e fica com a diferença (~US$ 18 com 3 lojas), "
        "desde que ninguém dispare com cartão da loja vencido e ninguém ligue o US$ 15 em cima da loja.",
        SOFT,
        TEAL,
    ))
    story.append(p(
        "Documento gerado para uso interno Genesis / Pello Menos. Atualizar o valor da Franqueadora sempre que N mudar. "
        "Não gravar cartão, CVV, senha ou PIT neste PDF.",
        "Small",
    ))

    def first_page(canvas, doc_):
        cover_header_footer(canvas, doc_)

    def later_pages(canvas, doc_):
        header_footer(canvas, doc_)

    doc.build(story, onFirstPage=first_page, onLaterPages=later_pages)
    print("OK", OUT, "bytes", OUT.stat().st_size)


if __name__ == "__main__":
    build()
