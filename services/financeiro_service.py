import os
from datetime import datetime
from database import get_connection, EXPORTS_DIR
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

class FinanceiroService:
    @staticmethod
    def set_department_budget(departamento, limite_mensal):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with get_connection() as conn:
            conn.execute("""
                INSERT INTO orcamento_departamentos (departamento, limite_mensal, created_at)
                VALUES (?, ?, ?)
                ON CONFLICT(departamento) DO UPDATE SET limite_mensal = excluded.limite_mensal;
            """, (departamento.strip(), float(limite_mensal), now))
            conn.commit()

    @staticmethod
    def normalize_year_month(val):
        """Converte entradas como '10/2026', '10-2026', '2026-10', '10/26' para 'YYYY-MM'."""
        if not val:
            return datetime.now().strftime("%Y-%m")
        val_str = str(val).strip()
        if not val_str:
            return datetime.now().strftime("%Y-%m")

        val_clean = val_str.replace(".", "/").replace("-", "/")
        parts = [p.strip() for p in val_clean.split("/") if p.strip()]
        if len(parts) == 2:
            if len(parts[0]) <= 2 and len(parts[1]) == 4:
                m = int(parts[0])
                y = int(parts[1])
                return f"{y:04d}-{m:02d}"
            elif len(parts[0]) == 4 and len(parts[1]) <= 2:
                y = int(parts[0])
                m = int(parts[1])
                return f"{y:04d}-{m:02d}"
            elif len(parts[0]) <= 2 and len(parts[1]) == 2:
                m = int(parts[0])
                y = 2000 + int(parts[1])
                return f"{y:04d}-{m:02d}"

        digits = "".join(c for c in val_str if c.isdigit())
        if len(digits) == 6:
            if 1990 <= int(digits[:4]) <= 2099:
                return f"{digits[:4]}-{digits[4:]}"
            elif 1990 <= int(digits[2:]) <= 2099:
                return f"{digits[2:]}-{digits[:2]}"

        return val_str

    @staticmethod
    def get_cost_center_summary(ano_mes=None):
        """
        Retorna o consumo financeiro por departamento/centro de custo comparado ao orçamento mensal.
        ano_mes: string 'YYYY-MM' ou 'MM/YYYY' (se None, utiliza o mês atual).
        """
        ano_mes = FinanceiroService.normalize_year_month(ano_mes)

        with get_connection() as conn:
            # 1. Busca todos os departamentos
            deptos_rows = conn.execute("SELECT DISTINCT departamento FROM funcionarios WHERE departamento IS NOT NULL AND departamento != ''").fetchall()
            deptos = [r["departamento"] for r in deptos_rows]

            # 2. Busca orçamentos cadastrados
            budgets_rows = conn.execute("SELECT departamento, limite_mensal FROM orcamento_departamentos").fetchall()
            budgets_map = {r["departamento"]: r["limite_mensal"] for r in budgets_rows}

            # 3. Busca gastos do mês
            expenses_rows = conn.execute("""
                SELECT f.departamento,
                       COUNT(m.id) as total_entregas,
                       SUM(m.quantidade) as total_itens,
                       SUM(m.custo_total) as gasto_total
                FROM movimentacoes m
                JOIN funcionarios f ON m.funcionario_id = f.id
                WHERE m.tipo = 'SAIDA' AND strftime('%Y-%m', m.data_hora) = ?
                GROUP BY f.departamento;
            """, (ano_mes,)).fetchall()
            expenses_map = {r["departamento"]: r for r in expenses_rows}

            results = []
            for d in deptos:
                exp = expenses_map.get(d)
                gasto = float(exp["gasto_total"] or 0.0) if exp else 0.0
                itens = int(exp["total_itens"] or 0) if exp else 0
                entregas = int(exp["total_entregas"] or 0) if exp else 0
                orcamento = float(budgets_map.get(d, 5000.0))

                saldo = orcamento - gasto
                pct = round((gasto / orcamento) * 100, 1) if orcamento > 0 else 0.0

                if pct > 100:
                    status = "ESTOURADO"
                    status_lbl = f"🔴 {pct}% (Excedeu R$ {abs(saldo):.2f})"
                elif pct >= 80:
                    status = "ALERTA"
                    status_lbl = f"🟡 {pct}% (Alerta de Limite)"
                else:
                    status = "REGULAR"
                    status_lbl = f"🟢 {pct}% (Dentro da Meta)"

                results.append({
                    "departamento": d,
                    "orcamento_mensal": orcamento,
                    "gasto_total": gasto,
                    "saldo_restante": saldo,
                    "percentual_usado": pct,
                    "total_itens": itens,
                    "total_entregas": entregas,
                    "status": status,
                    "status_label": status_lbl
                })

            results.sort(key=lambda x: x["gasto_total"], reverse=True)
            return results

    @staticmethod
    def generate_cost_center_pdf(ano_mes=None, output_path=None):
        if not ano_mes:
            ano_mes = datetime.now().strftime("%Y-%m")

        items = FinanceiroService.get_cost_center_summary(ano_mes)

        if not output_path:
            os.makedirs(EXPORTS_DIR, exist_ok=True)
            output_path = os.path.join(EXPORTS_DIR, f"Relatorio_Rateio_Custos_{ano_mes}.pdf")

        doc = SimpleDocTemplate(output_path, pagesize=A4, rightMargin=25, leftMargin=25, topMargin=25, bottomMargin=25)
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle('TStyle', parent=styles['Heading1'], fontSize=16, leading=20, textColor=colors.HexColor('#1E3A8A'), alignment=1)
        sub_style = ParagraphStyle('SStyle', parent=styles['Normal'], fontSize=9, leading=13, textColor=colors.HexColor('#64748B'), alignment=1, spaceAfter=18)
        c_bold = ParagraphStyle('CBold', parent=styles['Normal'], fontSize=8, leading=10, fontName='Helvetica-Bold')
        c_norm = ParagraphStyle('CNorm', parent=styles['Normal'], fontSize=8, leading=10)

        elements = []
        elements.append(Paragraph("RELATÓRIO FINANCEIRO DE RATEIO POR CENTRO DE CUSTO", title_style))
        elements.append(Paragraph(f"Apuração Consolidada de Consumo de EPIs — Competência: <b>{ano_mes}</b>", sub_style))

        # Cabeçalho da Tabela
        table_data = [
            [
                Paragraph("Centro de Custo / Setor", c_bold),
                Paragraph("Orçamento Mensal", c_bold),
                Paragraph("Gasto Apurado", c_bold),
                Paragraph("Saldo Restante", c_bold),
                Paragraph("% Consumido", c_bold),
                Paragraph("Itens Retirados", c_bold),
                Paragraph("Situação Orçamentária", c_bold)
            ]
        ]

        total_orc = sum(i["orcamento_mensal"] for i in items)
        total_gasto = sum(i["gasto_total"] for i in items)
        total_itens = sum(i["total_itens"] for i in items)

        for i in items:
            cor = "#DC2626" if i["status"] == "ESTOURADO" else ("#D97706" if i["status"] == "ALERTA" else "#059669")
            table_data.append([
                Paragraph(f"<b>{i['departamento']}</b>", c_norm),
                Paragraph(f"R$ {i['orcamento_mensal']:.2f}", c_norm),
                Paragraph(f"<b>R$ {i['gasto_total']:.2f}</b>", c_norm),
                Paragraph(f"R$ {i['saldo_restante']:.2f}", c_norm),
                Paragraph(f"{i['percentual_usado']}%", c_norm),
                Paragraph(f"{i['total_itens']} un", c_norm),
                Paragraph(f"<font color='{cor}'><b>{i['status_label']}</b></font>", c_norm)
            ])

        # Linha Totalizadora
        table_data.append([
            Paragraph("<b>TOTAL GERAL</b>", c_bold),
            Paragraph(f"<b>R$ {total_orc:.2f}</b>", c_bold),
            Paragraph(f"<b>R$ {total_gasto:.2f}</b>", c_bold),
            Paragraph(f"<b>R$ {(total_orc - total_gasto):.2f}</b>", c_bold),
            Paragraph(f"<b>{round((total_gasto/total_orc)*100, 1) if total_orc>0 else 0}%</b>", c_bold),
            Paragraph(f"<b>{total_itens} un</b>", c_bold),
            Paragraph("<b>CONSOLIDADO</b>", c_bold)
        ])

        col_widths = [115, 75, 75, 75, 60, 60, 85]
        t = Table(table_data, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A8A')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#F1F5F9')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))

        elements.append(t)
        doc.build(elements)
        return output_path
