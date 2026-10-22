import os
from datetime import datetime, timedelta
from database import get_connection, EXPORTS_DIR
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

class ValidadeUsoService:
    @staticmethod
    def get_items_due_for_exchange(status_filtro="TODOS"):
        """
        Retorna todos os EPIs atualmente em uso pelos colaboradores,
        calculando o tempo restante até a data recomendada de troca.
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            # Busca saídas que não foram integralmente devolvidas
            rows = cursor.execute("""
                SELECT m.id as mov_id, m.data_hora, m.quantidade, m.motivo,
                       e.id as epi_id, e.nome as epi_nome, e.codigo as epi_codigo, e.ca as epi_ca,
                       COALESCE(e.dias_vida_util, 90) as dias_vida_util,
                       f.id as func_id, f.nome as func_nome, f.matricula as func_matricula,
                       f.cargo as func_cargo, f.departamento as func_depto,
                       COALESCE(mc.periodicidade_dias, e.dias_vida_util, 90) as periodicidade
                FROM movimentacoes m
                JOIN epis e ON m.epi_id = e.id
                JOIN funcionarios f ON m.funcionario_id = f.id
                LEFT JOIN matriz_cargos_epis mc ON (mc.cargo = f.cargo AND mc.epi_id = e.id)
                WHERE m.tipo = 'SAIDA' AND f.status = 'Ativo'
                ORDER BY m.data_hora ASC;
            """).fetchall()

            # Busca devoluções por colaborador e epi para abater
            devs = cursor.execute("""
                SELECT funcionario_id, epi_id, SUM(quantidade) as total_dev
                FROM movimentacoes
                WHERE tipo IN ('DEVOLUCAO', 'EXTRAVIO_DEMISSAO')
                GROUP BY funcionario_id, epi_id;
            """).fetchall()
            dev_map = {(d["funcionario_id"], d["epi_id"]): d["total_dev"] for d in devs}

            now = datetime.now()
            results = []

            for r in rows:
                f_id = r["func_id"]
                e_id = r["epi_id"]

                # Verifica saldo pendente com o colaborador
                total_devolvido = dev_map.get((f_id, e_id), 0)
                if total_devolvido >= r["quantidade"]:
                    dev_map[(f_id, e_id)] = total_devolvido - r["quantidade"]
                    continue
                else:
                    dev_map[(f_id, e_id)] = 0

                # Data da entrega
                dt_str = r["data_hora"][:10]
                try:
                    dt_entrega = datetime.strptime(dt_str, "%Y-%m-%d")
                except Exception:
                    continue

                periodicidade = r["periodicidade"] if r["periodicidade"] and r["periodicidade"] > 0 else 90
                dt_venc = dt_entrega + timedelta(days=periodicidade)
                dias_restantes = (dt_venc.date() - now.date()).days

                if dias_restantes < 0:
                    st = "VENCIDO"
                    st_label = f"🔴 Vencido há {abs(dias_restantes)} dias"
                elif dias_restantes <= 15:
                    st = "VENCE_EM_BREVE"
                    st_label = f"🟡 Vence em {dias_restantes} dias"
                else:
                    st = "EM_DIA"
                    st_label = f"🟢 Vence em {dias_restantes} dias"

                if status_filtro != "TODOS" and st != status_filtro:
                    continue

                results.append({
                    "mov_id": r["mov_id"],
                    "func_id": f_id,
                    "func_nome": r["func_nome"],
                    "func_matricula": r["func_matricula"],
                    "func_cargo": r["func_cargo"],
                    "func_depto": r["func_depto"],
                    "epi_id": e_id,
                    "epi_nome": r["epi_nome"],
                    "epi_codigo": r["epi_codigo"],
                    "epi_ca": r["epi_ca"],
                    "data_entrega": dt_entrega.strftime("%d/%m/%Y"),
                    "data_previsao_troca": dt_venc.strftime("%d/%m/%Y"),
                    "periodicidade_dias": periodicidade,
                    "dias_restantes": dias_restantes,
                    "status": st,
                    "status_label": st_label
                })

            results.sort(key=lambda x: x["dias_restantes"])
            return results

    @staticmethod
    def generate_convocacao_pdf(items_to_summon, output_path=None):
        """
        Gera ordem oficial em PDF convocando os colaboradores com EPIs vencidos ou prestes a vencer
        para comparecerem ao almoxarifado para substituição preventiva (NR-6 Item 6.6.1).
        """
        if not output_path:
            os.makedirs(EXPORTS_DIR, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(EXPORTS_DIR, f"Convocacao_Troca_EPI_{ts}.pdf")

        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=25, leftMargin=25,
            topMargin=25, bottomMargin=25
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontSize=15,
            leading=18,
            textColor=colors.HexColor('#1E3A8A'),
            alignment=1,
            spaceAfter=4
        )
        subtitle_style = ParagraphStyle(
            'SubTitleStyle',
            parent=styles['Normal'],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor('#475569'),
            alignment=1,
            spaceAfter=15
        )
        cell_style = ParagraphStyle('CellStyle', parent=styles['Normal'], fontSize=8, leading=10)
        cell_bold = ParagraphStyle('CellBold', parent=styles['Normal'], fontSize=8, leading=10, fontName='Helvetica-Bold')

        elements = []
        elements.append(Paragraph("ORDEM DE CONVOCAÇÃO PARA TROCA PREVENTIVA DE EPI", title_style))
        elements.append(Paragraph("Em cumprimento à NR-6 do Ministério do Trabalho e Emprego — Gestão de Vida Útil e Proteção Ocupacional", subtitle_style))

        # Tabela de Itens Convocados
        table_data = [
            [
                Paragraph("Colaborador / Matrícula", cell_bold),
                Paragraph("Cargo / Setor", cell_bold),
                Paragraph("EPI a Substituir", cell_bold),
                Paragraph("C.A.", cell_bold),
                Paragraph("Data Entrega", cell_bold),
                Paragraph("Previsão Troca", cell_bold),
                Paragraph("Situação", cell_bold)
            ]
        ]

        for it in items_to_summon:
            cor_st = "#DC2626" if it["status"] == "VENCIDO" else ("#D97706" if it["status"] == "VENCE_EM_BREVE" else "#059669")
            st_p = Paragraph(f"<font color='{cor_st}'><b>{it['status_label']}</b></font>", cell_style)

            table_data.append([
                Paragraph(f"<b>{it['func_nome']}</b><br/>Matrícula: {it['func_matricula']}", cell_style),
                Paragraph(f"{it['func_cargo']}<br/>{it['func_depto']}", cell_style),
                Paragraph(f"<b>{it['epi_codigo']}</b> - {it['epi_nome']}", cell_style),
                Paragraph(str(it['epi_ca']), cell_style),
                Paragraph(it['data_entrega'], cell_style),
                Paragraph(f"<b>{it['data_previsao_troca']}</b>", cell_style),
                st_p
            ])

        col_widths = [120, 100, 125, 40, 55, 55, 80]
        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A8A')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))

        elements.append(table)
        elements.append(Spacer(1, 20))
        elements.append(Paragraph("<b>Instruções:</b> Os colaboradores listados acima devem comparecer ao almoxarifado munidos dos equipamentos usados para conferência do estado físico, devolução do item desgastado e recebimento do novo equipamento com assinatura do termo de cautela.", subtitle_style))

        doc.build(elements)
        return output_path
