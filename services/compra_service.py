import os
from datetime import datetime
from database import get_connection, EXPORTS_DIR
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import pandas as pd

class CompraService:
    @staticmethod
    def get_critical_stock_for_purchase():
        """Retorna todos os EPIs com estoque abaixo ou igual ao mínimo com sugestão de compra."""
        with get_connection() as conn:
            rows = conn.execute("""
                SELECT id, codigo, nome, ca, tamanho, quantidade, estoque_minimo,
                       preco_unitario, fabricante
                FROM epis
                WHERE ativo = 1 AND quantidade <= estoque_minimo
                ORDER BY quantidade ASC;
            """).fetchall()

            items = []
            for r in rows:
                qtd_atual = r["quantidade"]
                minimo = r["estoque_minimo"]
                sugestao = max(minimo * 2 - qtd_atual, 10)
                preco = float(r["preco_unitario"] or 0.0)
                estimado = sugestao * preco

                items.append({
                    "id": r["id"],
                    "codigo": r["codigo"],
                    "nome": r["nome"],
                    "ca": r["ca"],
                    "tamanho": r["tamanho"] or "Único",
                    "quantidade": qtd_atual,
                    "estoque_minimo": minimo,
                    "sugestao_compra": sugestao,
                    "preco_unitario": preco,
                    "custo_estimado": estimado,
                    "fabricante": r["fabricante"] or "-"
                })

            return items

    @staticmethod
    def list_suppliers():
        with get_connection() as conn:
            rows = conn.execute("SELECT * FROM fornecedores WHERE ativo = 1 ORDER BY razao_social ASC").fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def create_supplier(razao_social, cnpj="", contato="", email="", telefone="", cidade_uf=""):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO fornecedores (razao_social, cnpj, contato, email, telefone, cidade_uf, ativo, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?)
            """, (razao_social.strip(), cnpj.strip(), contato.strip(), email.strip(), telefone.strip(), cidade_uf.strip(), now))
            conn.commit()
            return cursor.lastrowid

    @staticmethod
    def generate_purchase_order_pdf(supplier=None, items=None, output_path=None):
        """Gera Ordem de Compra / Pedido de Cotação formal em PDF."""
        if items is None:
            items = CompraService.get_critical_stock_for_purchase()

        if not items:
            raise ValueError("Nenhum item com estoque crítico para gerar pedido de compra!")

        if not output_path:
            os.makedirs(EXPORTS_DIR, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(EXPORTS_DIR, f"Ordem_Compra_EPI_{ts}.pdf")

        # Dados da Empresa
        with get_connection() as conn:
            cfg = {r["chave"]: r["valor"] for r in conn.execute("SELECT chave, valor FROM configuracoes").fetchall()}

        emp_nome = cfg.get("empresa_nome", "EMPRESA INDUSTRIAL LTDA")
        emp_cnpj = cfg.get("empresa_cnpj", "00.000.000/0001-00")
        emp_end = cfg.get("empresa_endereco", "Distrito Industrial")

        doc = SimpleDocTemplate(output_path, pagesize=A4, rightMargin=25, leftMargin=25, topMargin=25, bottomMargin=25)
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle('TStyle', parent=styles['Heading1'], fontSize=16, leading=20, textColor=colors.HexColor('#1E3A8A'), alignment=1)
        sub_style = ParagraphStyle('SStyle', parent=styles['Normal'], fontSize=9, leading=13, textColor=colors.HexColor('#64748B'), alignment=1, spaceAfter=15)
        c_bold = ParagraphStyle('CBold', parent=styles['Normal'], fontSize=8, leading=10, fontName='Helvetica-Bold')
        c_norm = ParagraphStyle('CNorm', parent=styles['Normal'], fontSize=8, leading=10)

        elements = []
        elements.append(Paragraph("SOLICITAÇÃO DE COMPRA & COTAÇÃO DE EPIS", title_style))
        elements.append(Paragraph(f"{emp_nome} | CNPJ: {emp_cnpj} — {emp_end}", sub_style))

        # Dados do Fornecedor (se fornecido)
        forn_nome = supplier.get("razao_social") if supplier else "A/C: Departamento Comercial / Fornecedor"
        forn_contato = f"Contato: {supplier.get('contato', '-')} | E-mail: {supplier.get('email', '-')} | Tel: {supplier.get('telefone', '-')}" if supplier else "Cotação aberta de reposição de estoque emergencial"

        f_data = [
            [Paragraph(f"<b>DESTINATÁRIO:</b> {forn_nome}", c_norm), Paragraph(f"<b>DATA DA ORDEM:</b> {datetime.now().strftime('%d/%m/%Y')}", c_norm)],
            [Paragraph(forn_contato, c_norm), Paragraph("<b>TIPO:</b> Reposição de Estoque Mínimo (NR-6)", c_norm)]
        ]
        t_forn = Table(f_data, colWidths=[360, 185])
        t_forn.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(t_forn)
        elements.append(Spacer(1, 10))

        # Tabela de Itens
        table_data = [
            [
                Paragraph("Cód.", c_bold),
                Paragraph("Descrição do Equipamento (EPI)", c_bold),
                Paragraph("C.A.", c_bold),
                Paragraph("Tam.", c_bold),
                Paragraph("Saldo", c_bold),
                Paragraph("Qtd Solicitada", c_bold),
                Paragraph("Custo Unit. Estimado", c_bold),
                Paragraph("Total Estimado", c_bold)
            ]
        ]

        total_geral = 0.0
        total_pecas = 0

        for it in items:
            total_geral += it["custo_estimado"]
            total_pecas += it["sugestao_compra"]

            table_data.append([
                Paragraph(it["codigo"], c_norm),
                Paragraph(f"<b>{it['nome']}</b>", c_norm),
                Paragraph(str(it["ca"]), c_norm),
                Paragraph(it["tamanho"], c_norm),
                Paragraph(f"<font color='#EF4444'><b>{it['quantidade']}</b></font>", c_norm),
                Paragraph(f"<b>{it['sugestao_compra']} un</b>", c_bold),
                Paragraph(f"R$ {it['preco_unitario']:.2f}", c_norm),
                Paragraph(f"R$ {it['custo_estimado']:.2f}", c_norm)
            ])

        # Linha Total
        table_data.append([
            Paragraph("<b>TOTAL</b>", c_bold),
            Paragraph(f"<b>{len(items)} itens a repor</b>", c_bold),
            Paragraph("", c_norm),
            Paragraph("", c_norm),
            Paragraph("", c_norm),
            Paragraph(f"<b>{total_pecas} un</b>", c_bold),
            Paragraph("", c_norm),
            Paragraph(f"<b>R$ {total_geral:,.2f}</b>".replace(",", "X").replace(".", ",").replace("X", "."), c_bold)
        ])

        col_w = [55, 185, 45, 45, 40, 60, 60, 55]
        t_items = Table(table_data, colWidths=col_w, repeatRows=1)
        t_items.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A8A')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#F1F5F9')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(t_items)
        elements.append(Spacer(1, 20))

        # Rodapé de Aprovação
        sig_data = [
            [Paragraph("____________________________________________<br/><b>Responsável Almoxarifado / Solicitante</b>", c_norm),
             Paragraph("____________________________________________<br/><b>Aprovação Compras / Financeiro</b>", c_norm)]
        ]
        t_sig = Table(sig_data, colWidths=[270, 270])
        t_sig.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
        elements.append(t_sig)

        doc.build(elements)
        return output_path
