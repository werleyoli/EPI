import os
from datetime import datetime, timedelta
from database import get_connection, EXPORTS_DIR
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

class InspecaoService:
    @staticmethod
    def register_inspection(epi_id, numero_serie, data_inspecao, validade_meses,
                            responsavel_tecnico, resultado, observacoes=""):
        if not responsavel_tecnico or not responsavel_tecnico.strip():
            raise ValueError("O nome do responsável técnico pela inspeção é obrigatório!")

        from services.movement_service import MovementService
        data_norm = MovementService.normalize_date_iso(data_inspecao) or datetime.now().strftime("%Y-%m-%d")
        dt_insp = datetime.strptime(data_norm, "%Y-%m-%d")
        dt_prox = dt_insp + timedelta(days=validade_meses * 30)

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO inspecoes_epi (epi_id, numero_serie, data_inspecao, data_proxima_inspecao,
                                          responsavel_tecnico, resultado, observacoes, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                epi_id,
                numero_serie.strip() if numero_serie else "-",
                dt_insp.strftime("%Y-%m-%d"),
                dt_prox.strftime("%Y-%m-%d"),
                responsavel_tecnico.strip(),
                resultado.strip().upper(),
                observacoes.strip() if observacoes else "",
                now
            ))
            conn.commit()

            from services.audit_service import AuditService
            AuditService.log(
                acao="INSPECAO_REGISTRADA",
                modulo="INSPECOES",
                detalhes=f"Inspeção técnica {resultado} p/ EPI ID {epi_id}, Série: {numero_serie}. Resp: {responsavel_tecnico}"
            )

            return cursor.lastrowid

    @staticmethod
    def list_inspections(resultado=None):
        with get_connection() as conn:
            query = """
                SELECT i.id, i.epi_id, i.numero_serie, i.data_inspecao, i.data_proxima_inspecao,
                       i.responsavel_tecnico, i.resultado, i.observacoes,
                       e.codigo as epi_codigo, e.nome as epi_nome, e.ca as epi_ca, e.fabricante
                FROM inspecoes_epi i
                JOIN epis e ON i.epi_id = e.id
                WHERE 1=1
            """
            params = []
            if resultado and resultado != "TODOS":
                query += " AND i.resultado = ?"
                params.append(resultado)

            query += " ORDER BY i.data_proxima_inspecao ASC;"
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def get_expired_or_due_inspections():
        with get_connection() as conn:
            now_str = datetime.now().strftime("%Y-%m-%d")
            limit_str = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
            rows = conn.execute("""
                SELECT i.id, i.numero_serie, i.data_proxima_inspecao, i.resultado,
                       e.nome as epi_nome, e.codigo as epi_codigo, e.ca as epi_ca
                FROM inspecoes_epi i
                JOIN epis e ON i.epi_id = e.id
                WHERE i.data_proxima_inspecao <= ?
                ORDER BY i.data_proxima_inspecao ASC;
            """, (limit_str,)).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def generate_laudo_pdf(inspecao_id, output_path=None):
        """Gera laudo formal em PDF de inspeção periódica de EPI em altura/espaço confinado."""
        with get_connection() as conn:
            row = conn.execute("""
                SELECT i.*, e.nome as epi_nome, e.codigo as epi_codigo, e.ca as epi_ca,
                       e.fabricante, e.tamanho as epi_tamanho
                FROM inspecoes_epi i
                JOIN epis e ON i.epi_id = e.id
                WHERE i.id = ?;
            """, (inspecao_id,)).fetchone()
            if not row:
                raise ValueError("Inspeção não encontrada!")
            insp = dict(row)

        if not output_path:
            os.makedirs(EXPORTS_DIR, exist_ok=True)
            output_path = os.path.join(EXPORTS_DIR, f"Laudo_Inspecao_{insp['epi_codigo']}_{insp['id']}.pdf")

        doc = SimpleDocTemplate(output_path, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle('TStyle', parent=styles['Heading1'], fontSize=16, leading=20, textColor=colors.HexColor('#1E3A8A'), alignment=1)
        sub_style = ParagraphStyle('SStyle', parent=styles['Normal'], fontSize=9, leading=13, textColor=colors.HexColor('#64748B'), alignment=1, spaceAfter=20)
        c_bold = ParagraphStyle('CBold', parent=styles['Normal'], fontSize=9, leading=12, fontName='Helvetica-Bold')
        c_norm = ParagraphStyle('CNorm', parent=styles['Normal'], fontSize=9, leading=12)

        elements = []
        elements.append(Paragraph("LAUDO TÉCNICO DE INSPEÇÃO PERIÓDICA DE EPI", title_style))
        elements.append(Paragraph("Conforme Norma Regulamentadora NR-35 (Trabalho em Altura) e NR-33 (Espaço Confinado)", sub_style))

        # Dados do Equipamento
        eq_data = [
            [Paragraph("DADOS DO EQUIPAMENTO INSPECIONADO", c_bold), Paragraph("", c_norm)],
            [Paragraph("Descrição do EPI:", c_bold), Paragraph(insp["epi_nome"], c_norm)],
            [Paragraph("Código Interno / C.A.:", c_bold), Paragraph(f"{insp['epi_codigo']} | C.A. {insp['epi_ca']}", c_norm)],
            [Paragraph("Fabricante / Tamanho:", c_bold), Paragraph(f"{insp.get('fabricante') or '-'} | {insp.get('epi_tamanho') or '-'}", c_norm)],
            [Paragraph("Nº de Série / Lote / Patrimônio:", c_bold), Paragraph(insp["numero_serie"] or "-", c_norm)],
            [Paragraph("Data da Inspeção:", c_bold), Paragraph(insp["data_inspecao"], c_norm)],
            [Paragraph("Próxima Inspeção Obrigatória:", c_bold), Paragraph(insp["data_proxima_inspecao"], c_norm)],
            [Paragraph("Responsável Técnico / Inspetor:", c_bold), Paragraph(insp["responsavel_tecnico"], c_norm)],
            [Paragraph("PARECER / RESULTADO:", c_bold), Paragraph(f"<b><font color='{'#10B981' if insp['resultado']=='APROVADO' else '#EF4444'}'>{insp['resultado']}</font></b>", c_bold)],
            [Paragraph("Observações Técnicas / Desgaste:", c_bold), Paragraph(insp.get("observacoes") or "Equipamento em perfeitas condições de uso, sem fissuras, deformações ou desgastes anormais.", c_norm)],
        ]

        t = Table(eq_data, colWidths=[180, 350])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F1F5F9')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))

        elements.append(t)
        elements.append(Spacer(1, 30))

        # Assinaturas
        sig_data = [
            [Paragraph("____________________________________________<br/><b>Inspetor Técnico / SST</b>", c_norm),
             Paragraph("____________________________________________<br/><b>Responsável Almoxarifado / Segurança</b>", c_norm)]
        ]
        t_sig = Table(sig_data, colWidths=[260, 260])
        t_sig.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
        elements.append(t_sig)

        doc.build(elements)
        return output_path
