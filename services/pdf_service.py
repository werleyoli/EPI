import os
from datetime import datetime, timedelta
from collections import defaultdict
import unicodedata
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable
from database import get_connection, EXPORTS_DIR

class PDFService:
    @staticmethod
    def get_company_info():
        with get_connection() as conn:
            rows = conn.execute("SELECT chave, valor FROM configuracoes").fetchall()
            configs = {r["chave"]: r["valor"] for r in rows}
        return {
            "nome": configs.get("empresa_nome", "EMPRESA INDUSTRIAL LTDA"),
            "cnpj": configs.get("empresa_cnpj", "00.000.000/0001-00"),
            "endereco": configs.get("empresa_endereco", "Endereço da Empresa"),
            "responsavel": configs.get("responsavel_seguranca", "Segurança do Trabalho"),
            "termo": configs.get("termo_nr6", (
                "Declaro ter recebido da empresa os Equipamentos de Proteção Individual (EPI) abaixo relacionados, "
                "novos e em perfeitas condições de uso, devidamente aprovados pelo Ministério do Trabalho (C.A. válido). "
                "Comprometo-me a utilizá-los estritamente no exercício de minhas atividades, zelando por sua guarda e "
                "conservação, comunicando imediatamente qualquer alteração que os torne impróprios para uso (NR-6)."
            ))
        }

    @staticmethod
    def _create_signature_rl_image(img_path, max_w=85, max_h=22):
        if not img_path or not os.path.exists(img_path):
            return None
        try:
            from PIL import Image as PILImage
            from reportlab.platypus import Image as RLImage
            with PILImage.open(img_path) as pil_im:
                orig_w, orig_h = pil_im.size
            if orig_w <= 0 or orig_h <= 0:
                return None
            aspect = orig_w / float(orig_h)
            w = max_w
            h = w / aspect
            if h > max_h:
                h = max_h
                w = h * aspect
            return RLImage(img_path, width=w, height=h)
        except Exception:
            return None

    @staticmethod
    def generate_employee_sheet_pdf(employee, items=None, filepath=None, only_blank=False, sheet_title=None):
        """Gera a Ficha Oficial de EPI do Colaborador (NR-6)."""
        if items is None:
            items = []

        if not filepath:
            os.makedirs(EXPORTS_DIR, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = "".join(c for c in employee['nome'] if c.isalnum() or c in (' ', '_')).rstrip()
            prefix = "folha_em_branco_epi" if only_blank else "ficha_epi"
            filepath = os.path.abspath(os.path.join(EXPORTS_DIR, f"{prefix}_{safe_name}_{timestamp}.pdf"))

        doc = SimpleDocTemplate(
            filepath,
            pagesize=landscape(A4),
            leftMargin=20,
            rightMargin=20,
            topMargin=20,
            bottomMargin=20
        )

        company = PDFService.get_company_info()
        styles = getSampleStyleSheet()

        # Estilos customizados
        title_style = ParagraphStyle(
            'DocTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=13,
            leading=15,
            alignment=1, # Centralizado
            textColor=colors.HexColor('#1E293B')
        )
        subtitle_style = ParagraphStyle(
            'DocSubtitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=10,
            leading=12,
            alignment=1,
            textColor=colors.HexColor('#475569')
        )
        term_style = ParagraphStyle(
            'TermText',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=7.5,
            leading=9.5,
            alignment=4, # Justificado
            textColor=colors.HexColor('#334155')
        )
        cell_style = ParagraphStyle(
            'CellText',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=7.5,
            leading=9,
            alignment=0
        )
        cell_center = ParagraphStyle(
            'CellCenter',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=7.5,
            leading=9,
            alignment=1
        )
        cell_bold = ParagraphStyle(
            'CellBold',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=7.5,
            leading=9,
            alignment=1,
            textColor=colors.white
        )

        story = []

        # Cabeçalho da Empresa
        if only_blank:
            page_text = "<b>Página:</b> Continuação / Folha Adicional"
        else:
            page_text = f"<b>Página:</b> {sheet_title or '1/1'}"

        header_table_data = [
            [
                Paragraph(f"<b>{company['nome'].upper()}</b><br/>CNPJ: {company['cnpj']}<br/>{company['endereco']}", cell_style),
                Paragraph("<b>FICHA DE CONTROLE E ENTREGA DE EPI</b><br/>Norma Regulamentadora NR-6 - Portaria 3.214/78 MTE", title_style),
                Paragraph(f"<b>Data Emissão:</b> {datetime.now().strftime('%d/%m/%Y')}<br/>{page_text}", cell_style)
            ]
        ]
        header_table = Table(header_table_data, colWidths=[220, 360, 220])
        header_table.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#94A3B8')),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
            ('PADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 6))

        # Dados do Funcionário
        func_info_data = [
            [
                Paragraph(f"<b>Colaborador:</b> {employee['nome']}", cell_style),
                Paragraph(f"<b>Matrícula:</b> {employee['matricula']}", cell_style),
                Paragraph(f"<b>CPF:</b> {employee.get('cpf') or 'N/A'}", cell_style),
            ],
            [
                Paragraph(f"<b>Função / Cargo:</b> {employee['cargo']}", cell_style),
                Paragraph(f"<b>Setor / Depto:</b> {employee['departamento']}", cell_style),
                Paragraph(f"<b>Admissão:</b> {employee.get('data_admissao') or 'N/A'}", cell_style),
            ]
        ]
        func_table = Table(func_info_data, colWidths=[300, 250, 250])
        func_table.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 0.75, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FFFFFF')),
            ('PADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(func_table)
        story.append(Spacer(1, 6))

        # Termo de Responsabilidade NR-6
        termo_p = Paragraph(f"<b>TERMO DE COMPROMISSO E GUARDA DE EPI:</b> {company['termo']}", term_style)
        termo_table = Table([[termo_p]], colWidths=[800])
        termo_table.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F1F5F9')),
            ('PADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(termo_table)
        story.append(Spacer(1, 8))

        # Tabela de Entregas de EPI
        table_headers = [
            Paragraph("Data / Hora", cell_bold),
            Paragraph("Tipo", cell_bold),
            Paragraph("Equipamento de Proteção (EPI)", cell_bold),
            Paragraph("C.A.", cell_bold),
            Paragraph("Validade", cell_bold),
            Paragraph("Fabr. / Tam.", cell_bold),
            Paragraph("Qtd", cell_bold),
            Paragraph("Valor Unit.", cell_bold),
            Paragraph("Motivo", cell_bold),
            Paragraph("Quem Entregou", cell_bold),
            Paragraph("Assinatura do Empregado", cell_bold)
        ]

        def _sanitize_motivo(motivo_val, tipo_val="SAIDA"):
            if not motivo_val:
                return "Entrega de EPI Obrigatório" if tipo_val == "SAIDA" else "Devolução de EPI"
            m = str(motivo_val).strip()
            m_lower = m.lower()
            if "retroativ" in m_lower or "histór" in m_lower or "histor" in m_lower:
                if "admiss" in m_lower:
                    return "Admissional / Kit Obrigatório"
                elif "troca" in m_lower or "desgaste" in m_lower:
                    return "Troca Periódica por Desgaste"
                elif "danific" in m_lower:
                    return "Substituição de Equipamento"
                else:
                    return "Entrega de EPI Obrigatório" if tipo_val == "SAIDA" else "Devolução de EPI"
            return m

        table_rows = [table_headers]

        if not only_blank and items:
            # Ordenação cronológica de cima para baixo (da entrega mais antiga para a mais recente)
            sorted_items = sorted(items, key=lambda x: (str(x.get("data_hora", "")), int(x.get("id", 0) or 0)))
            for item in sorted_items:
                dt_str = item.get("data_hora", "")
                try:
                    dt_fmt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
                except Exception:
                    dt_fmt = dt_str

                fab = (item.get('epi_fabricante') or '-').strip()
                # Prioriza tamanho unitário entregue e higieniza contra múltiplas variações
                tam = (item.get('tamanho') or item.get('mov_tamanho') or item.get('epi_tamanho') or '-').strip()
                if "," in tam:
                    candidates = [c.strip() for c in tam.split(",") if c.strip()]
                    c_uni = str(item.get("tamanho_uniforme") or employee.get("tamanho_uniforme") or "").strip()
                    c_calc = str(item.get("tamanho_calcado") or employee.get("tamanho_calcado") or "").strip()
                    c_luva = str(item.get("tamanho_luva") or employee.get("tamanho_luva") or "").strip()
                    matched_tam = None
                    for c in candidates:
                        if c_uni and c_uni not in ("-", "") and c.upper() == c_uni.upper():
                            matched_tam = c
                            break
                        if c_calc and c_calc not in ("-", "") and c.upper() == c_calc.upper():
                            matched_tam = c
                            break
                        if c_luva and c_luva not in ("-", "") and c.upper() == c_luva.upper():
                            matched_tam = c
                            break
                    tam = matched_tam if matched_tam else "Único"

                if fab != '-' and tam != '-' and tam.upper() not in ('ÚNICO', 'UNICO'):
                    fab_tam = f"<b>{fab}</b><br/><font color='#475569'>Tam: {tam}</font>"
                elif fab != '-':
                    if tam != '-' and tam.upper() not in ('ÚNICO', 'UNICO'):
                        fab_tam = f"<b>{fab}</b><br/><font color='#475569'>Tam: {tam}</font>"
                    else:
                        fab_tam = f"<b>{fab}</b>"
                else:
                    fab_tam = f"Tam: {tam}" if (tam != '-' and tam.upper() not in ('ÚNICO', 'UNICO')) else "-"
                
                # Célula de assinatura com proporção natural preservada
                sig_cell = Paragraph("&nbsp;", cell_style)
                sig_path = item.get("assinatura_path")
                if sig_path:
                    real_sig_path = None
                    if os.path.isabs(sig_path) and os.path.exists(sig_path):
                        real_sig_path = sig_path
                    elif os.path.exists(os.path.join(EXPORTS_DIR, "signatures", os.path.basename(sig_path))):
                        real_sig_path = os.path.join(EXPORTS_DIR, "signatures", os.path.basename(sig_path))
                    from database import SIGNATURES_DIR
                    if not real_sig_path and os.path.exists(os.path.join(SIGNATURES_DIR, os.path.basename(sig_path))):
                        real_sig_path = os.path.join(SIGNATURES_DIR, os.path.basename(sig_path))

                    if real_sig_path:
                        rl_img = PDFService._create_signature_rl_image(real_sig_path, max_w=85, max_h=22)
                        if rl_img:
                            sig_cell = rl_img
                        else:
                            sig_cell = Paragraph("Assinado Digitalmente", cell_center)

                tipo_item = item.get("tipo", "SAIDA")
                mov_est = str(item.get("mov_estado") or "").upper()
                if tipo_item in ("NÃO DEVOLVIDO", "EXTRAVIO_DEMISSAO") or "NÃO DEVOLV" in mov_est or "RETIDO" in mov_est:
                    tipo_p = Paragraph("<font color='#DC2626'><b>[NÃO DEV.]</b></font>", cell_center)
                elif tipo_item == "DEVOLUCAO":
                    tipo_p = Paragraph("<font color='#16A34A'><b>DEVOLUÇÃO</b></font>", cell_center)
                else:
                    tipo_p = Paragraph(tipo_item, cell_center)

                val_u = float(item.get("custo_unitario") or item.get("valor_unitario") or item.get("epi_preco") or 0.0)
                val_u_str = f"R$ {val_u:.2f}" if val_u > 0 else "-"

                clean_motivo = _sanitize_motivo(item.get("motivo", ""), tipo_item)

                d_vida = int(item.get("dias_vida_util") or item.get("epi_dias_vida_util") or 0)
                if d_vida > 0:
                    try:
                        dt_base = datetime.strptime(str(dt_str)[:10], "%Y-%m-%d").date()
                    except Exception:
                        try:
                            dt_base = datetime.strptime(str(dt_str)[:10], "%d/%m/%Y").date()
                        except Exception:
                            dt_base = datetime.now().date()
                    dt_venc = dt_base + timedelta(days=d_vida)
                    val_dt_fmt = dt_venc.strftime("%d/%m/%Y")
                    mes_lbl = f"{d_vida // 30}m" if (d_vida % 30 == 0 and d_vida >= 30) else f"{d_vida}d"
                    val_disp = f"<b>{val_dt_fmt}</b><br/><font size=6.5 color='#475569'>({mes_lbl})</font>"
                else:
                    val_disp = "-"
                val_p = Paragraph(val_disp, cell_center)

                est_raw = str(item.get("mov_estado") or item.get("estado_conservacao") or "NOVO").upper()
                if any(k in est_raw for k in ["USADO", "REUTIL", "BOM", "HIGIEN"]):
                    cond_tag = "USADO"
                    cond_color = "#B45309"
                elif any(k in est_raw for k in ["RUIM", "MANUT"]):
                    cond_tag = "MANUTENÇÃO"
                    cond_color = "#DC2626"
                elif any(k in est_raw for k in ["DESC", "SUCATA"]):
                    cond_tag = "DESCARTE"
                    cond_color = "#991B1B"
                else:
                    cond_tag = "NOVO"
                    cond_color = "#047857"

                cond_badge = f"<font size=6.5 color='{cond_color}'><b>[{cond_tag}]</b></font>"
                epi_desc = f"<b>{item.get('epi_nome', '')}</b> ({item.get('epi_codigo','')})<br/>{cond_badge}"

                table_rows.append([
                    Paragraph(dt_fmt, cell_center),
                    tipo_p,
                    Paragraph(epi_desc, cell_style),
                    Paragraph(str(item.get("epi_ca", "")), cell_center),
                    val_p,
                    Paragraph(fab_tam, cell_style),
                    Paragraph(f"{item.get('quantidade', 1)} {item.get('epi_unidade', 'UN')}", cell_center),
                    Paragraph(val_u_str, cell_center),
                    Paragraph(clean_motivo, cell_style),
                    Paragraph(f"<b>{item.get('responsavel_entrega', '')}</b>", cell_style),
                    sig_cell
                ])

        # Se for folha em branco ou tiver menos linhas que o padrão:
        # Garante 14 linhas uniformes para folha em branco, ou no mínimo 12 para regular
        target_rows = 14 if only_blank else max(12, len(table_rows) - 1)
        while len(table_rows) - 1 < target_rows:
            table_rows.append([
                Paragraph("&nbsp;", cell_center),
                Paragraph("&nbsp;", cell_center),
                Paragraph("&nbsp;", cell_style),
                Paragraph("&nbsp;", cell_center),
                Paragraph("&nbsp;", cell_center),
                Paragraph("&nbsp;", cell_style),
                Paragraph("&nbsp;", cell_center),
                Paragraph("&nbsp;", cell_center),
                Paragraph("&nbsp;", cell_style),
                Paragraph("&nbsp;", cell_style),
                Paragraph("&nbsp;", cell_style)
            ])

        col_widths = [70, 42, 155, 40, 55, 85, 35, 55, 80, 85, 98]
        # Altura dinâmica (None) para as linhas com dados para NUNCA vazar nem sobrepor cabeçalho;
        # Altura fixa de 20pt para linhas vazias de preenchimento.
        num_data_rows = len(items) if (not only_blank and items) else 0
        num_blank_rows = len(table_rows) - 1 - num_data_rows
        row_heights = [24] + [None] * num_data_rows + [20] * num_blank_rows
        items_table = Table(table_rows, colWidths=col_widths, rowHeights=row_heights, repeatRows=1)
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E3A8A')),
            ('ALIGN', (0,0), (-1,0), 'CENTER'),
            ('VALIGN', (0,0), (-1,0), 'MIDDLE'),
            ('VALIGN', (0,1), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#94A3B8')),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')]),
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ('LEFTPADDING', (0,0), (-1,-1), 3),
            ('RIGHTPADDING', (0,0), (-1,-1), 3),
        ]))
        story.append(items_table)
        story.append(Spacer(1, 15))

        # Encontra a assinatura mais recente do colaborador para estampar no rodapé
        latest_sig_path = None
        if not only_blank and items:
            from database import SIGNATURES_DIR
            for it in items:
                sp = it.get("assinatura_path")
                if sp:
                    cand = None
                    if os.path.isabs(sp) and os.path.exists(sp):
                        cand = sp
                    elif os.path.exists(os.path.join(EXPORTS_DIR, "signatures", os.path.basename(sp))):
                        cand = os.path.join(EXPORTS_DIR, "signatures", os.path.basename(sp))
                    elif os.path.exists(os.path.join(SIGNATURES_DIR, os.path.basename(sp))):
                        cand = os.path.join(SIGNATURES_DIR, os.path.basename(sp))
                    if cand:
                        latest_sig_path = cand
                        break

        colab_footer = []
        if latest_sig_path:
            rl_ft = PDFService._create_signature_rl_image(latest_sig_path, max_w=130, max_h=34)
            if rl_ft:
                colab_footer.append(rl_ft)
            else:
                colab_footer.append(Spacer(1, 28))
        else:
            colab_footer.append(Spacer(1, 28))
        colab_footer.append(Paragraph("___________________________________________________<br/><b>Assinatura do Empregado</b>", cell_center))

        resp_footer = [
            Spacer(1, 28),
            Paragraph("___________________________________________________<br/><b>Responsável Técnico / Almoxarifado</b>", cell_center)
        ]

        # Rodapé de Assinaturas
        footer_data = [
            [
                colab_footer,
                resp_footer
            ]
        ]
        footer_table = Table(footer_data, colWidths=[400, 400])
        footer_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'BOTTOM'),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('PADDING', (0,0), (-1,-1), 2),
        ]))
        story.append(KeepTogether(footer_table))

        doc.build(story)
        return filepath

    @staticmethod
    def generate_movements_report_pdf(movements, filters_desc="Geral", filepath=None):
        """Gera relatório de saídas e movimentações em PDF."""
        if not filepath:
            os.makedirs(EXPORTS_DIR, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = os.path.abspath(os.path.join(EXPORTS_DIR, f"relatorio_saidas_{timestamp}.pdf"))

        doc = SimpleDocTemplate(
            filepath,
            pagesize=landscape(A4),
            leftMargin=20,
            rightMargin=20,
            topMargin=20,
            bottomMargin=20
        )

        company = PDFService.get_company_info()
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'DocTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=13,
            leading=15,
            alignment=1,
            textColor=colors.HexColor('#1E293B')
        )
        cell_style = ParagraphStyle('CellText', parent=styles['Normal'], fontName='Helvetica', fontSize=7.5, leading=9)
        cell_center = ParagraphStyle('CellCenter', parent=styles['Normal'], fontName='Helvetica', fontSize=7.5, leading=9, alignment=1)
        cell_bold = ParagraphStyle('CellBold', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=7.5, leading=9, alignment=1, textColor=colors.white)

        story = []

        header_data = [
            [
                Paragraph(f"<b>{company['nome'].upper()}</b><br/>CNPJ: {company['cnpj']}", cell_style),
                Paragraph("<b>RELATÓRIO DE SAÍDAS E MOVIMENTAÇÕES DE EPI</b>", title_style),
                Paragraph(f"<b>Emissão:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}<br/><b>Filtro:</b> {filters_desc}", cell_style)
            ]
        ]
        header_table = Table(header_data, colWidths=[220, 360, 220])
        header_table.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#94A3B8')),
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('PADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 10))

        headers = [
            Paragraph("Data / Hora", cell_bold),
            Paragraph("Tipo", cell_bold),
            Paragraph("Código", cell_bold),
            Paragraph("Nome do EPI", cell_bold),
            Paragraph("C.A.", cell_bold),
            Paragraph("Qtd", cell_bold),
            Paragraph("Condição", cell_bold),
            Paragraph("Funcionário / Destino", cell_bold),
            Paragraph("Quem Entregou", cell_bold),
            Paragraph("Motivo", cell_bold),
        ]

        rows = [headers]
        total_saidas = 0
        total_itens = 0
        total_nao_devolvidos = 0

        for m in movements:
            dt_str = m.get("data_hora", "")
            try:
                dt_fmt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
            except Exception:
                dt_fmt = dt_str

            qtd = m.get("quantidade", 0)
            total_itens += qtd
            t_raw = m.get("tipo", "")
            est_raw = str(m.get("estado_conservacao") or m.get("mov_estado") or "").upper()
            is_nao_dev = t_raw in ("NÃO DEVOLVIDO", "EXTRAVIO_DEMISSAO") or "NÃO DEVOLV" in est_raw or "NAO DEVOLV" in est_raw or "RETIDO" in est_raw

            if is_nao_dev:
                total_nao_devolvidos += qtd
                tipo_p = Paragraph("<font color='#DC2626'><b>[NÃO DEV.]</b></font>", cell_center)
                cond_p = Paragraph("<font color='#DC2626'><b>[NÃO DEVOLVIDO]</b></font>", cell_center)
            elif t_raw == "SAIDA":
                total_saidas += qtd
                tipo_p = Paragraph("<font color='#1E40AF'><b>SAÍDA</b></font>", cell_center)
                cond_p = Paragraph("Novo" if "NOVO" in est_raw else ("Reutilizado" if "BOM" in est_raw or "REUTIL" in est_raw else "-"), cell_center)
            elif t_raw == "DEVOLUCAO":
                tipo_p = Paragraph("<font color='#16A34A'><b>DEVOLUÇÃO</b></font>", cell_center)
                if any(k in est_raw for k in ["DESC", "SUCATA", "INSERV"]):
                    cond_p = Paragraph("<font color='#B91C1C'><b>[Descarte]</b></font>", cell_center)
                elif any(k in est_raw for k in ["RUIM", "MANUT", "REPAR"]):
                    cond_p = Paragraph("<font color='#D97706'><b>[Manutenção]</b></font>", cell_center)
                else:
                    cond_p = Paragraph("<font color='#16A34A'><b>Bom / Reutil.</b></font>", cell_center)
            elif t_raw == "ENTRADA":
                tipo_p = Paragraph("<font color='#059669'><b>ENTRADA</b></font>", cell_center)
                cond_p = Paragraph("Novo" if "NOVO" in est_raw else "-", cell_center)
            else:
                tipo_p = Paragraph(t_raw, cell_center)
                cond_p = Paragraph(est_raw or "-", cell_center)

            func_info = f"<b>{m.get('func_nome') or 'Almoxarifado'}</b>"
            if m.get("func_matricula"):
                func_info += f" ({m.get('func_matricula')})"
            if m.get("func_cargo"):
                func_info += f"<br/><font color='#64748B'>{m.get('func_cargo')}</font>"

            rows.append([
                Paragraph(dt_fmt, cell_center),
                tipo_p,
                Paragraph(m.get("epi_codigo", ""), cell_center),
                Paragraph(m.get("epi_nome", ""), cell_style),
                Paragraph(str(m.get("epi_ca", "") or "-"), cell_center),
                Paragraph(f"{qtd} {m.get('epi_unidade', 'UN')}", cell_center),
                cond_p,
                Paragraph(func_info, cell_style),
                Paragraph(f"<b>{m.get('responsavel_entrega', '')}</b>", cell_style),
                Paragraph(m.get("motivo", ""), cell_style),
            ])

        col_w = [80, 80, 45, 145, 40, 40, 80, 125, 80, 85]
        t = Table(rows, colWidths=col_w, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F172A')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')]),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('PADDING', (0,0), (-1,-1), 3),
        ]))
        story.append(t)
        story.append(Spacer(1, 10))

        # Resumo final
        summary_text = (
            f"<b>Total de Registros:</b> {len(movements)} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Total de Unidades Movimentadas:</b> {total_itens} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Total em Saídas p/ Colaboradores:</b> {total_saidas} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>[!] Itens Não Devolvidos:</b> <font color='#DC2626'><b>{total_nao_devolvidos}</b></font>"
        )
        summary_table = Table([[Paragraph(summary_text, cell_style)]], colWidths=[800])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#E2E8F0')),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#94A3B8')),
            ('PADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(summary_table)

        doc.build(story)
        return filepath

    @staticmethod
    def classify_epi_group(nome):
        """Classifica o EPI em famílias/grupos lógicos com base na denominação técnica."""
        if not nome:
            return "GRUPO: DIVERSOS"
        n = unicodedata.normalize('NFKD', str(nome)).encode('ASCII', 'ignore').decode('ASCII').upper().strip()

        # Botas específicas
        if "BOTA" in n and "PVC" in n:
            return "GRUPO: BOTA DE PVC"
        if "BOTA" in n and ("TERMICA" in n or "FRIGORIF" in n):
            return "GRUPO: BOTA TÉRMICA"
        if any(k in n for k in ["BOTINA", "BOTA", "SAPATO", "CALCADO", "TENIS"]):
            return "GRUPO: CALÇADOS & BOTINAS DE SEGURANÇA"

        # Camisas e Uniformes
        if any(k in n for k in ["CAMISA", "CAMISETA", "POLO", "BLUSA"]):
            return "GRUPO: CAMISAS DE SEGURANÇA / UNIFORMES"
        if any(k in n for k in ["MACACAO", "JAPONA", "CALCA", "UNIFORME", "AVENTAL", "VESTIMENTA"]):
            return "GRUPO: VESTIMENTAS & UNIFORMES"

        # Luvas
        if "LUVA" in n:
            if "VAQUETA" in n or "RASPA" in n:
                return "GRUPO: LUVAS DE VAQUETA / RASPA"
            if "NITRILICA" in n or "LATEX" in n or "BORRACHA" in n:
                return "GRUPO: LUVAS NITRÍLICAS / BORRACHA"
            if "ANTICORTE" in n or "PU" in n:
                return "GRUPO: LUVAS ANTICORTE / PU"
            return "GRUPO: LUVAS DE PROTEÇÃO"

        # Proteção Cabeça e Olhos
        if "CAPACETE" in n:
            return "GRUPO: CAPACETES DE SEGURANÇA"
        if any(k in n for k in ["OCULOS", "VISOR", "MASCARA DE SOLDA", "ESCUDO"]):
            return "GRUPO: ÓCULOS & PROTEÇÃO FACIAL"

        # Proteção Auditiva e Respiratória
        if any(k in n for k in ["AUDITIVO", "ABAFADOR", "PLUG"]):
            return "GRUPO: PROTEÇÃO AUDITIVA"
        if any(k in n for k in ["RESPIRADOR", "MASCARA", "PFF1", "PFF2", "PFF3", "FILTRO"]):
            return "GRUPO: PROTEÇÃO RESPIRATÓRIA"

        # Trabalho em Altura
        if any(k in n for k in ["CINTO", "TALABARTE", "TRAVA-QUEDAS", "MOSQUETAO", "CORDA"]):
            return "GRUPO: TRABALHO EM ALTURA"

        # Fallback inteligente: primeiras 2 palavras
        words = n.split()
        if len(words) >= 2:
            return f"GRUPO: {' '.join(words[:2])}"
        elif words:
            return f"GRUPO: {words[0]}"
        return "GRUPO: DIVERSOS"

    @staticmethod
    def generate_grouped_inventory_pdf(epis, only_in_stock=True, filepath=None):
        """
        Gera relatório profissional de inventário físico em PDF (A4 Paisagem).
        Agrupa os itens por Família/Grupo (ex: GRUPO DE BOTA PVC, GRUPO DE BOTA TÉRMICA, etc.)
        com totalização detalhada de quantidades por tamanho em cada grupo.
        """
        if only_in_stock:
            epis = [e for e in epis if float(e.get("quantidade", 0) or 0) > 0]

        if not filepath:
            os.makedirs(EXPORTS_DIR, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = os.path.abspath(os.path.join(EXPORTS_DIR, f"inventario_estoque_grupos_{ts}.pdf"))

        doc = SimpleDocTemplate(
            filepath,
            pagesize=landscape(A4),
            leftMargin=20,
            rightMargin=20,
            topMargin=20,
            bottomMargin=20
        )

        company = PDFService.get_company_info()
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'DocTitleInv',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=13,
            leading=15,
            alignment=1,
            textColor=colors.HexColor('#0F172A')
        )
        cell_style = ParagraphStyle('CellTextInv', parent=styles['Normal'], fontName='Helvetica', fontSize=7.5, leading=9)
        cell_center = ParagraphStyle('CellCenterInv', parent=styles['Normal'], fontName='Helvetica', fontSize=7.5, leading=9, alignment=1)
        cell_right = ParagraphStyle('CellRightInv', parent=styles['Normal'], fontName='Helvetica', fontSize=7.5, leading=9, alignment=2)
        cell_bold_center = ParagraphStyle('CellBoldCenterInv', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=7.5, leading=9, alignment=1, textColor=colors.white)

        group_header_style = ParagraphStyle(
            'GroupHeaderInv',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9.5,
            leading=11,
            textColor=colors.HexColor('#1E3A8A')
        )
        sizes_summary_style = ParagraphStyle(
            'SizesSummaryInv',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8,
            leading=10,
            textColor=colors.HexColor('#0369A1')
        )

        story = []

        # Cabeçalho da Empresa
        header_data = [
            [
                Paragraph(f"<b>{company['nome'].upper()}</b><br/>CNPJ: {company['cnpj']}<br/>Almoxarifado Central & SST", cell_style),
                Paragraph("<b>RELATÓRIO DE INVENTÁRIO FÍSICO DE ESTOQUE DE EPI</b><br/><font size=8 color='#475569'>ITENS COM SALDO ATIVO - AGRUPADOS POR FAMÍLIA & GRADE DE TAMANHOS</font>", title_style),
                Paragraph(f"<b>Emissão:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}<br/><b>Filtro:</b> Somente com Saldo (> 0)<br/><b>Padrão:</b> NR-6 MTE", cell_style)
            ]
        ]
        header_table = Table(header_data, colWidths=[200, 400, 200])
        header_table.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#94A3B8')),
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('PADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 8))

        # Agrupar os EPIs - APENAS SALDO ATIVO UTILIZÁVEL (Novo + Usado Bom)
        # Itens em Manutenção e Descarte NÃO entram no estoque físico ativo!
        grouped = defaultdict(list)
        total_unidades_geral = 0
        total_valor_geral = 0.0

        for e in epis:
            from services.epi_service import EPIService
            grades = EPIService.get_epi_grades(e.get("id"))
            if grades:
                qtd_ativa = sum(int(g.get("total_disponivel", 0) or 0) for g in grades)
            else:
                qtd_ativa = int(e.get("quantidade", 0) or 0)

            if only_in_stock and qtd_ativa <= 0:
                continue

            grp_raw = (e.get("grupo") or "").strip()
            if grp_raw and grp_raw.upper() not in ["GERAL", "NONE", "NULL"]:
                grp = f"GRUPO: {grp_raw.upper()}" if not grp_raw.upper().startswith("GRUPO") else grp_raw.upper()
            else:
                grp = "GRUPO: DIVERSOS / OUTROS"
            grouped[grp].append(e)

            preco = float(e.get("preco_unitario", 0.0) or 0.0)
            total_unidades_geral += qtd_ativa
            total_valor_geral += (qtd_ativa * preco)

        # Painel Resumo Executivo (KPIs)
        val_geral_fmt = f"R$ {total_valor_geral:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        kpi_data = [
            [
                Paragraph(f"<b>SKUs em Estoque:</b> {len(epis)} itens", cell_center),
                Paragraph(f"<b>Grupos/Famílias:</b> {len(grouped)} famílias", cell_center),
                Paragraph(f"<b>Saldo Físico Ativo:</b> {total_unidades_geral} peças/pares", cell_center),
                Paragraph(f"<b>Patrimônio em Estoque:</b> {val_geral_fmt}", cell_center),
            ]
        ]
        kpi_table = Table(kpi_data, colWidths=[200, 200, 200, 200])
        kpi_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#E2E8F0')),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('PADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(kpi_table)
        story.append(Spacer(1, 10))

        col_widths = [50, 195, 45, 120, 55, 85, 45, 50, 75, 80]

        def _format_estado_label(est_raw):
            e = (str(est_raw) or "").upper().strip()
            if "NOVO" in e:
                return "<font color='#15803D'><b>Novo</b></font>"
            elif "BOM" in e or "REUTIL" in e or "USADO" in e:
                return "<font color='#1D4ED8'><b>Usado (Bom)</b></font>"
            elif "RUIM" in e or "MANUT" in e or "REPAR" in e:
                return "<font color='#B45309'><b>Manutenção</b></font>"
            elif "DESC" in e or "SUCATA" in e or "INSERV" in e:
                return "<font color='#B91C1C'><b>Descarte</b></font>"
            return f"<b>{est_raw or 'Novo'}</b>"

        for grp_name in sorted(grouped.keys()):
            items = grouped[grp_name]

            # Calcula resumo de tamanhos deste grupo (APENAS ESTOQUE ATIVO: NOVO e BOM)
            sizes_count = defaultdict(int)
            grp_qtd_total = 0
            grp_valor_total = 0.0

            for it in items:
                pu = float(it.get("preco_unitario", 0.0) or 0.0)
                from services.epi_service import EPIService
                grades = EPIService.get_epi_grades(it.get("id"))
                if grades:
                    for g in grades:
                        tam_g = str(g.get("tamanho", "") or "").strip() or "Único"
                        q_disp = int(g.get("total_disponivel", 0) or 0)
                        if q_disp > 0:
                            sizes_count[tam_g] += q_disp
                            grp_qtd_total += q_disp
                            grp_valor_total += (q_disp * pu)
                else:
                    q = int(it.get("quantidade", 0) or 0)
                    tam = str(it.get("tamanho", "") or "").strip() or "Único"
                    if q > 0:
                        sizes_count[tam] += q
                        grp_qtd_total += q
                        grp_valor_total += (q * pu)

            # Formata grade de tamanhos em destaque: ex: "Tam 38: 5 un | Tam 39: 10 un..."
            sorted_sizes = sorted(sizes_count.keys())
            sizes_str_list = [f"<b>{s}:</b> {sizes_count[s]} un" for s in sorted_sizes if sizes_count[s] > 0]
            if not sizes_str_list:
                sizes_str_list = [f"<b>{s}:</b> 0 un" for s in sorted_sizes]
            sizes_summary_text = " &nbsp;|&nbsp; ".join(sizes_str_list)

            # Barra de identificação do Grupo com Resumo de Tamanhos
            grp_bar = [
                [
                    Paragraph(f"<b>{grp_name.upper()}</b> ({len(items)} SKU{'s' if len(items)>1 else ''})", group_header_style),
                    Paragraph(f"<b>Grade por Tamanho:</b> {sizes_summary_text}", sizes_summary_style)
                ]
            ]
            t_grp_bar = Table(grp_bar, colWidths=[280, 520])
            t_grp_bar.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#EFF6FF')),
                ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#93C5FD')),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('PADDING', (0,0), (-1,-1), 4),
            ]))

            table_rows = [
                [
                    Paragraph("Código", cell_bold_center),
                    Paragraph("Descrição do Equipamento (EPI)", cell_bold_center),
                    Paragraph("C.A.", cell_bold_center),
                    Paragraph("Fabricante / Marca", cell_bold_center),
                    Paragraph("Tamanho", cell_bold_center),
                    Paragraph("Estado do Material", cell_bold_center),
                    Paragraph("Localização", cell_bold_center),
                    Paragraph("Saldo", cell_bold_center),
                    Paragraph("Preço Unit.", cell_bold_center),
                    Paragraph("Total R$", cell_bold_center),
                ]
            ]

            for it in items:
                pu = float(it.get("preco_unitario", 0.0) or 0.0)
                from services.epi_service import EPIService
                stock_items = EPIService.get_epi_stock_items(it.get("id"))

                # Se o item possui variações físicas (tamanho e estado), gera linha para cada um
                loc_pdf = str(it.get("localizacao") or "-")
                if it.get("localizacao_secundaria"):
                    loc_pdf = f"{loc_pdf} | {it['localizacao_secundaria']}" if loc_pdf != "-" else str(it["localizacao_secundaria"])

                if stock_items:
                    # Filtra APENAS itens utilizáveis (NOVO ou BOM/REUTILIZÁVEL) com saldo ativo
                    # Itens em MANUTENÇÃO e DESCARTE são excluídos do inventário físico ativo!
                    filtered_active = []
                    for s in stock_items:
                        st_u = str(s.get("estado") or "").upper()
                        if any(k in st_u for k in ["DESC", "SUCATA", "INSERV", "RUIM", "MANUT", "REPAR"]):
                            continue
                        if only_in_stock and int(s.get("quantidade", 0) or 0) <= 0:
                            continue
                        filtered_active.append(s)

                    active_items = filtered_active

                    if active_items:
                        def _sort_key_item(val):
                            s = str(val.get("tamanho", "")).strip()
                            try:
                                return (0, int(s), val.get("estado", ""))
                            except ValueError:
                                order = {"PP": 1, "P": 2, "M": 3, "G": 4, "GG": 5, "XG": 6, "XXG": 7, "ÚNICO": 8, "UNICO": 8}
                                return (1, order.get(s.upper(), 99), s, val.get("estado", ""))

                        active_items.sort(key=_sort_key_item)

                        for s_it in active_items:
                            tam_g = str(s_it.get("tamanho", "") or "").strip() or "Único"
                            q_g = int(s_it.get("quantidade", 0) or 0)
                            tot_g = q_g * pu
                            est_display = _format_estado_label(s_it.get("estado", "NOVO"))

                            table_rows.append([
                                Paragraph(str(it.get("codigo", "")), cell_center),
                                Paragraph(str(it.get("nome", "")), cell_style),
                                Paragraph(str(it.get("ca", "-")), cell_center),
                                Paragraph(str(it.get("fabricante", "-") or "-"), cell_style),
                                Paragraph(f"<b>Tam. {tam_g}</b>", cell_center),
                                Paragraph(est_display, cell_center),
                                Paragraph(loc_pdf, cell_center),
                                Paragraph(f"<b>{q_g}</b> {it.get('unidade', 'UN')}", cell_center),
                                Paragraph(f"R$ {pu:.2f}", cell_right),
                                Paragraph(f"<b>R$ {tot_g:.2f}</b>", cell_right),
                            ])
                        continue

                # Se não tem variações de grade, gera a linha normal do item
                q = int(it.get("quantidade", 0) or 0)
                tot_item = q * pu
                tam_str = str(it.get("tamanho", "") or "").strip() or "Único"
                est_display = _format_estado_label("NOVO")

                table_rows.append([
                    Paragraph(str(it.get("codigo", "")), cell_center),
                    Paragraph(str(it.get("nome", "")), cell_style),
                    Paragraph(str(it.get("ca", "-")), cell_center),
                    Paragraph(str(it.get("fabricante", "-") or "-"), cell_style),
                    Paragraph(f"<b>{tam_str}</b>", cell_center),
                    Paragraph(est_display, cell_center),
                    Paragraph(loc_pdf, cell_center),
                    Paragraph(f"<b>{q}</b> {it.get('unidade', 'UN')}", cell_center),
                    Paragraph(f"R$ {pu:.2f}", cell_right),
                    Paragraph(f"<b>R$ {tot_item:.2f}</b>", cell_right),
                ])

            # Linha de subtotal do grupo (10 colunas)
            table_rows.append([
                Paragraph(f"<b>SUBTOTAL DO {grp_name}:</b>", cell_style),
                Paragraph(f"<b>{sizes_summary_text}</b>", cell_style),
                Paragraph("", cell_style),
                Paragraph("", cell_style),
                Paragraph("", cell_style),
                Paragraph("", cell_style),
                Paragraph("", cell_style),
                Paragraph(f"<b>{grp_qtd_total} un</b>", cell_center),
                Paragraph("Total:", cell_right),
                Paragraph(f"<b>R$ {grp_valor_total:.2f}</b>", cell_right),
            ])

            t_items = Table(table_rows, colWidths=col_widths, repeatRows=1)
            t_items.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E3A8A')),
                ('GRID', (0,0), (-1,-2), 0.5, colors.HexColor('#CBD5E1')),
                ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, colors.HexColor('#F8FAFC')]),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('PADDING', (0,0), (-1,-1), 3),
                ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#F1F5F9')),
                ('LINEABOVE', (0,-1), (-1,-1), 1, colors.HexColor('#1E3A8A')),
                ('SPAN', (0,-1), (1,-1)),
            ]))

            story.append(KeepTogether([t_grp_bar, Spacer(1, 2), t_items]))
            story.append(Spacer(1, 10))

        # Total Geral no Final
        tot_geral_rows = [
            [
                Paragraph("<b>TOTAL GERAL DO ESTOQUE FÍSICO DE EPI (NR-6):</b>", title_style),
                Paragraph(f"<b>{total_unidades_geral} peças/unidades &nbsp;&nbsp;|&nbsp;&nbsp; {val_geral_fmt}</b>", title_style)
            ]
        ]
        t_tot_geral = Table(tot_geral_rows, colWidths=[400, 400])
        t_tot_geral.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#DBEAFE')),
            ('BOX', (0,0), (-1,-1), 1.5, colors.HexColor('#1E3A8A')),
            ('PADDING', (0,0), (-1,-1), 6),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(Spacer(1, 6))
        story.append(t_tot_geral)

        # Assinaturas
        sign_data = [
            [
                Paragraph("____________________________________________<br/><b>Almoxarife / Responsável pelo Estoque</b>", cell_center),
                Paragraph("____________________________________________<br/><b>Técnico / Eng. de Segurança do Trabalho (SST)</b>", cell_center),
            ]
        ]
        t_sign = Table(sign_data, colWidths=[400, 400])
        t_sign.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('PADDING', (0,0), (-1,-1), 10),
        ]))
        story.append(Spacer(1, 22))
        story.append(t_sign)

        doc.build(story)
        return filepath

    @staticmethod
    def generate_maintenance_discard_pdf(filepath=None):
        """
        Gera relatório dedicado de EPIs em Manutenção, Descarte e Não Devolvidos.
        Totalmente separado do inventário físico ativo.
        """
        if not filepath:
            os.makedirs(EXPORTS_DIR, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = os.path.abspath(os.path.join(EXPORTS_DIR, f"relatorio_manutencao_descarte_{ts}.pdf"))

        doc = SimpleDocTemplate(
            filepath,
            pagesize=landscape(A4),
            leftMargin=20,
            rightMargin=20,
            topMargin=20,
            bottomMargin=20
        )

        company = PDFService.get_company_info()
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'DocTitleManut',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=13,
            leading=15,
            alignment=1,
            textColor=colors.HexColor('#7F1D1D')
        )
        cell_style = ParagraphStyle('CellTextM', parent=styles['Normal'], fontName='Helvetica', fontSize=7.5, leading=9)
        cell_center = ParagraphStyle('CellCenterM', parent=styles['Normal'], fontName='Helvetica', fontSize=7.5, leading=9, alignment=1)
        cell_right = ParagraphStyle('CellRightM', parent=styles['Normal'], fontName='Helvetica', fontSize=7.5, leading=9, alignment=2)
        cell_bold_center = ParagraphStyle('CellBoldCenterM', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=7.5, leading=9, alignment=1, textColor=colors.white)
        section_style = ParagraphStyle('SectionHeaderM', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, leading=12, textColor=colors.white)

        story = []

        # Cabeçalho da Empresa
        header_data = [
            [
                Paragraph(f"<b>{company['nome'].upper()}</b><br/>CNPJ: {company['cnpj']}<br/>Gestão de Estoque & SST", cell_style),
                Paragraph("<b>RELATÓRIO DE EPIS EM MANUTENÇÃO, DESCARTE E NÃO DEVOLVIDOS</b><br/><font size=8 color='#991B1B'>CONTROLE SEPARADO: REPARO, SUCATA E ITENS NÃO DEVOLVIDOS / RETIDOS (NR-6 / CLT)</font>", title_style),
                Paragraph(f"<b>Emissão:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}<br/><b>Status:</b> Quarentena / Baixas<br/><b>Padrão:</b> CLT & NR-6", cell_style)
            ]
        ]
        header_table = Table(header_data, colWidths=[200, 400, 200])
        header_table.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#DC2626')),
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FEF2F2')),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('PADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 10))

        # Busca dados do banco
        itens_manutencao = []
        itens_descarte = []
        itens_nao_devolvidos = []
        with get_connection() as conn:
            cursor = conn.cursor()
            # 1. Busca da grade (Itens físicos em Manutenção ou Descarte)
            query_grades = """
                SELECT g.id, g.epi_id, g.tamanho, g.estado, g.quantidade,
                       e.codigo as epi_codigo, e.nome as epi_nome, e.ca as epi_ca,
                       e.fabricante as epi_fabricante, e.unidade as epi_unidade,
                       COALESCE(e.preco_unitario, 0.0) as preco_unitario,
                       e.localizacao
                FROM epi_grades g
                JOIN epis e ON g.epi_id = e.id
                WHERE g.quantidade > 0
                  AND (
                      UPPER(g.estado) LIKE '%RUIM%' OR UPPER(g.estado) LIKE '%MANUT%' OR UPPER(g.estado) LIKE '%REPAR%'
                      OR UPPER(g.estado) LIKE '%DESC%' OR UPPER(g.estado) LIKE '%SUCATA%' OR UPPER(g.estado) LIKE '%INSERV%'
                  )
                ORDER BY e.nome ASC, g.tamanho ASC;
            """
            rows = cursor.execute(query_grades).fetchall()
            for r in rows:
                item = dict(r)
                st = str(item.get("estado", "")).upper()
                if any(k in st for k in ["DESC", "SUCATA", "INSERV"]):
                    itens_descarte.append(item)
                else:
                    itens_manutencao.append(item)

            # 2. Busca de Não Devolvidos / Retidos (Extravio / Cobrança TRCT)
            query_naodev = """
                SELECT m.id, m.epi_id, m.tamanho, m.quantidade, m.custo_unitario, m.custo_total,
                       m.data_hora, m.responsavel_entrega, m.motivo, m.estado_conservacao, m.observacao,
                       e.codigo as epi_codigo, e.nome as epi_nome, e.ca as epi_ca,
                       e.fabricante as epi_fabricante, e.unidade as epi_unidade,
                       COALESCE(m.custo_unitario, e.preco_unitario, 0.0) as preco_unitario,
                       f.nome as func_nome, f.matricula as func_matricula
                FROM movimentacoes m
                JOIN epis e ON m.epi_id = e.id
                LEFT JOIN funcionarios f ON m.funcionario_id = f.id
                WHERE m.tipo = 'NÃO DEVOLVIDO'
                   OR m.tipo = 'EXTRAVIO_DEMISSAO'
                   OR UPPER(m.estado_conservacao) LIKE '%NÃO DEVOLV%'
                   OR UPPER(m.estado_conservacao) LIKE '%NAO DEVOLV%'
                   OR UPPER(m.estado_conservacao) LIKE '%RETIDO%'
                ORDER BY m.data_hora DESC;
            """
            rows_nd = cursor.execute(query_naodev).fetchall()
            for rnd in rows_nd:
                itens_nao_devolvidos.append(dict(rnd))

        total_manut_qtd = sum(int(x["quantidade"]) for x in itens_manutencao)
        total_manut_val = sum(int(x["quantidade"]) * float(x["preco_unitario"]) for x in itens_manutencao)
        total_desc_qtd = sum(int(x["quantidade"]) for x in itens_descarte)
        total_desc_val = sum(int(x["quantidade"]) * float(x["preco_unitario"]) for x in itens_descarte)
        total_naodev_qtd = sum(int(x["quantidade"]) for x in itens_nao_devolvidos)
        total_naodev_val = sum(
            float(x.get("custo_total") or 0.0) if float(x.get("custo_total") or 0.0) > 0
            else int(x["quantidade"]) * float(x["preco_unitario"])
            for x in itens_nao_devolvidos
        )
        total_geral_qtd = total_manut_qtd + total_desc_qtd + total_naodev_qtd
        total_geral_val = total_manut_val + total_desc_val + total_naodev_val

        # KPIs
        kpi_data = [
            [
                Paragraph(f"<b>[1] Em Manutenção:</b><br/><font size=9.5 color='#B45309'><b>{total_manut_qtd} un (R$ {total_manut_val:.2f})</b></font>", cell_center),
                Paragraph(f"<b>[2] Em Descarte (Sucata):</b><br/><font size=9.5 color='#DC2626'><b>{total_desc_qtd} un (R$ {total_desc_val:.2f})</b></font>", cell_center),
                Paragraph(f"<b>[3] Não Devolvidos / Retidos:</b><br/><font size=9.5 color='#7F1D1D'><b>{total_naodev_qtd} un (R$ {total_naodev_val:.2f})</b></font>", cell_center),
                Paragraph(f"<b>Total Quarentena / Perdas:</b><br/><font size=9.5 color='#1E293B'><b>{total_geral_qtd} un (R$ {total_geral_val:.2f})</b></font>", cell_center),
            ]
        ]
        kpi_table = Table(kpi_data, colWidths=[200, 200, 200, 200])
        kpi_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(kpi_table)
        story.append(Spacer(1, 10))

        col_w = [60, 230, 45, 55, 100, 45, 75, 75, 115]

        # 1. Seção de Manutenção
        sec_manut_bar = Table([[Paragraph("<b>[1] ITENS EM MANUTENÇÃO / REPARO</b> (Quarentena Técnica - Aguardando Conserto/Higienização)", section_style)]], colWidths=[800])
        sec_manut_bar.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#D97706')),
            ('PADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(sec_manut_bar)
        story.append(Spacer(1, 2))

        headers_m = [
            Paragraph("Código", cell_bold_center),
            Paragraph("Equipamento (EPI)", cell_bold_center),
            Paragraph("Tam.", cell_bold_center),
            Paragraph("C.A.", cell_bold_center),
            Paragraph("Fabricante", cell_bold_center),
            Paragraph("Qtd", cell_bold_center),
            Paragraph("Custo Unit.", cell_bold_center),
            Paragraph("Total R$", cell_bold_center),
            Paragraph("Destinação Prevista", cell_bold_center),
        ]
        rows_manut = [headers_m]
        if itens_manutencao:
            for it in itens_manutencao:
                qtd_i = int(it["quantidade"])
                pu = float(it["preco_unitario"])
                tot_i = qtd_i * pu
                rows_manut.append([
                    Paragraph(str(it.get("epi_codigo", "")), cell_center),
                    Paragraph(str(it.get("epi_nome", "")), cell_style),
                    Paragraph(str(it.get("tamanho", "Único")), cell_center),
                    Paragraph(str(it.get("epi_ca", "-")), cell_center),
                    Paragraph(str(it.get("epi_fabricante", "-") or "-"), cell_style),
                    Paragraph(f"<b>{qtd_i}</b> {it.get('epi_unidade', 'UN')}", cell_center),
                    Paragraph(f"R$ {pu:.2f}", cell_right),
                    Paragraph(f"<b>R$ {tot_i:.2f}</b>", cell_right),
                    Paragraph("Avaliação Técnica / Conserto", cell_center),
                ])
            rows_manut.append([
                Paragraph("<b>SUBTOTAL MANUTENÇÃO:</b>", cell_style),
                Paragraph(f"<b>{len(itens_manutencao)} SKU(s)</b>", cell_style),
                Paragraph("", cell_center),
                Paragraph("", cell_center),
                Paragraph("", cell_center),
                Paragraph(f"<b>{total_manut_qtd} un</b>", cell_center),
                Paragraph("Total:", cell_right),
                Paragraph(f"<b>R$ {total_manut_val:.2f}</b>", cell_right),
                Paragraph("", cell_center),
            ])
        else:
            rows_manut.append([
                Paragraph("Nenhum item atualmente em manutenção ou reparo.", cell_style),
                Paragraph("", cell_style), Paragraph("", cell_style), Paragraph("", cell_style),
                Paragraph("", cell_style), Paragraph("0 un", cell_center), Paragraph("-", cell_right),
                Paragraph("R$ 0,00", cell_right), Paragraph("-", cell_center)
            ])

        t_manut = Table(rows_manut, colWidths=col_w)
        t_manut.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#92400E')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('ROWBACKGROUNDS', (0,1), (-1,-2 if itens_manutencao else -1), [colors.white, colors.HexColor('#FFFBEB')]),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('PADDING', (0,0), (-1,-1), 3),
        ]))
        if itens_manutencao:
            t_manut.setStyle(TableStyle([
                ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#FEF3C7')),
                ('LINEABOVE', (0,-1), (-1,-1), 1, colors.HexColor('#D97706')),
            ]))
        story.append(t_manut)
        story.append(Spacer(1, 10))

        # 2. Seção de Descarte Físico
        sec_desc_bar = Table([[Paragraph("<b>[2] ITENS EM DESCARTE / BAIXA</b> (Inservíveis / Sucata Físico - Fora do Estoque Físico)", section_style)]], colWidths=[800])
        sec_desc_bar.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#DC2626')),
            ('PADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(sec_desc_bar)
        story.append(Spacer(1, 2))

        rows_desc = [headers_m]
        if itens_descarte:
            for it in itens_descarte:
                qtd_i = int(it["quantidade"])
                pu = float(it["preco_unitario"])
                tot_i = qtd_i * pu
                rows_desc.append([
                    Paragraph(str(it.get("epi_codigo", "")), cell_center),
                    Paragraph(str(it.get("epi_nome", "")), cell_style),
                    Paragraph(str(it.get("tamanho", "Único")), cell_center),
                    Paragraph(str(it.get("epi_ca", "-")), cell_center),
                    Paragraph(str(it.get("epi_fabricante", "-") or "-"), cell_style),
                    Paragraph(f"<b>{qtd_i}</b> {it.get('epi_unidade', 'UN')}", cell_center),
                    Paragraph(f"R$ {pu:.2f}", cell_right),
                    Paragraph(f"<b>R$ {tot_i:.2f}</b>", cell_right),
                    Paragraph("Descarte NR-6 / Baixa", cell_center),
                ])
            rows_desc.append([
                Paragraph("<b>SUBTOTAL DESCARTE (PREJUÍZO SUCATA):</b>", cell_style),
                Paragraph(f"<b>{len(itens_descarte)} SKU(s)</b>", cell_style),
                Paragraph("", cell_center),
                Paragraph("", cell_center),
                Paragraph("", cell_center),
                Paragraph(f"<b>{total_desc_qtd} un</b>", cell_center),
                Paragraph("Perda Total:", cell_right),
                Paragraph(f"<b>R$ {total_desc_val:.2f}</b>", cell_right),
                Paragraph("", cell_center),
            ])
        else:
            rows_desc.append([
                Paragraph("Nenhum item atualmente marcado para descarte no galpão.", cell_style),
                Paragraph("", cell_style), Paragraph("", cell_style), Paragraph("", cell_style),
                Paragraph("", cell_style), Paragraph("0 un", cell_center), Paragraph("-", cell_right),
                Paragraph("R$ 0,00", cell_right), Paragraph("-", cell_center)
            ])

        t_desc = Table(rows_desc, colWidths=col_w)
        t_desc.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#991B1B')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('ROWBACKGROUNDS', (0,1), (-1,-2 if itens_descarte else -1), [colors.white, colors.HexColor('#FEF2F2')]),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('PADDING', (0,0), (-1,-1), 3),
        ]))
        if itens_descarte:
            t_desc.setStyle(TableStyle([
                ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#FEE2E2')),
                ('LINEABOVE', (0,-1), (-1,-1), 1, colors.HexColor('#DC2626')),
            ]))
        story.append(t_desc)
        story.append(Spacer(1, 10))

        # 3. Seção de Não Devolvidos / Retidos (Extravio / TRCT)
        sec_naodev_bar = Table([[Paragraph("<b>[3] ITENS NÃO DEVOLVIDOS / RETIDOS</b> (Extravio na Demissão / Notificação / Cobrança TRCT)", section_style)]], colWidths=[800])
        sec_naodev_bar.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#7F1D1D')),
            ('PADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(sec_naodev_bar)
        story.append(Spacer(1, 2))

        col_w_nd = [55, 175, 45, 50, 150, 75, 40, 65, 70, 75]
        headers_nd = [
            Paragraph("Código", cell_bold_center),
            Paragraph("Equipamento (EPI)", cell_bold_center),
            Paragraph("Tam.", cell_bold_center),
            Paragraph("C.A.", cell_bold_center),
            Paragraph("Colaborador / Matrícula", cell_bold_center),
            Paragraph("Data Reg.", cell_bold_center),
            Paragraph("Qtd", cell_bold_center),
            Paragraph("Custo Unit.", cell_bold_center),
            Paragraph("Prejuízo R$", cell_bold_center),
            Paragraph("Destinação Prevista", cell_bold_center),
        ]
        rows_nd = [headers_nd]
        if itens_nao_devolvidos:
            for it in itens_nao_devolvidos:
                qtd_i = int(it.get("quantidade") or 1)
                pu = float(it.get("preco_unitario") or it.get("custo_unitario") or 0.0)
                tot_i = float(it.get("custo_total") or 0.0)
                if tot_i <= 0 and pu > 0:
                    tot_i = qtd_i * pu

                dt_fmt = str(it.get("data_hora") or "")[:16]
                try:
                    dt_fmt = datetime.strptime(dt_fmt[:19], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
                except Exception:
                    pass

                f_nome = it.get("func_nome") or "Não identificado"
                f_matr = it.get("func_matricula")
                f_display = f"<b>{f_nome}</b>" + (f"<br/><font size=6.5 color='#475569'>Matr: {f_matr}</font>" if f_matr else "")

                rows_nd.append([
                    Paragraph(str(it.get("epi_codigo", "")), cell_center),
                    Paragraph(str(it.get("epi_nome", "")), cell_style),
                    Paragraph(str(it.get("tamanho", "Único")), cell_center),
                    Paragraph(str(it.get("epi_ca", "-")), cell_center),
                    Paragraph(f_display, cell_style),
                    Paragraph(dt_fmt, cell_center),
                    Paragraph(f"<b>{qtd_i}</b> {it.get('epi_unidade', 'UN')}", cell_center),
                    Paragraph(f"R$ {pu:.2f}", cell_right),
                    Paragraph(f"<b>R$ {tot_i:.2f}</b>", cell_right),
                    Paragraph("Cobrança TRCT / Notif.", cell_center),
                ])
            rows_nd.append([
                Paragraph("<b>SUBTOTAL NÃO DEVOLVIDOS (PREJUÍZO):</b>", cell_style),
                Paragraph(f"<b>{len(itens_nao_devolvidos)} Ocorrência(s)</b>", cell_style),
                Paragraph("", cell_center),
                Paragraph("", cell_center),
                Paragraph("", cell_center),
                Paragraph("", cell_center),
                Paragraph(f"<b>{total_naodev_qtd} un</b>", cell_center),
                Paragraph("Prejuízo:", cell_right),
                Paragraph(f"<b>R$ {total_naodev_val:.2f}</b>", cell_right),
                Paragraph("", cell_center),
            ])
        else:
            rows_nd.append([
                Paragraph("Nenhum item atualmente classificado como não devolvido ou retido.", cell_style),
                Paragraph("", cell_style), Paragraph("", cell_style), Paragraph("", cell_style),
                Paragraph("", cell_style), Paragraph("", cell_style), Paragraph("0 un", cell_center),
                Paragraph("-", cell_right), Paragraph("R$ 0,00", cell_right), Paragraph("-", cell_center)
            ])

        t_naodev = Table(rows_nd, colWidths=col_w_nd)
        t_naodev.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#7F1D1D')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('ROWBACKGROUNDS', (0,1), (-1,-2 if itens_nao_devolvidos else -1), [colors.white, colors.HexColor('#FEF2F2')]),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('PADDING', (0,0), (-1,-1), 3),
        ]))
        if itens_nao_devolvidos:
            t_naodev.setStyle(TableStyle([
                ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#FEE2E2')),
                ('LINEABOVE', (0,-1), (-1,-1), 1, colors.HexColor('#991B1B')),
            ]))
        story.append(t_naodev)
        story.append(Spacer(1, 12))

        # Total Geral Quarentena & Perdas
        tot_m_rows = [
            [
                Paragraph("<b>TOTAL GERAL (ITENS FORA DO ESTOQUE ATIVO - MANUTENÇÃO, DESCARTE E NÃO DEVOLVIDOS):</b>", title_style),
                Paragraph(f"<b>{total_geral_qtd} unidades &nbsp;&nbsp;|&nbsp;&nbsp; R$ {total_geral_val:.2f}</b>", title_style)
            ]
        ]
        t_tot_m = Table(tot_m_rows, colWidths=[470, 330])
        t_tot_m.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FEE2E2')),
            ('BOX', (0,0), (-1,-1), 1.5, colors.HexColor('#DC2626')),
            ('PADDING', (0,0), (-1,-1), 6),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(t_tot_m)
        story.append(Spacer(1, 16))

        # Assinaturas
        sign_data = [
            [
                Paragraph("____________________________________________<br/><b>Almoxarife / Controle de Estoque & Quarentena</b>", cell_center),
                Paragraph("____________________________________________<br/><b>Técnico / Eng. de Segurança do Trabalho (SST)</b>", cell_center),
            ]
        ]
        t_sign = Table(sign_data, colWidths=[400, 400])
        t_sign.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('PADDING', (0,0), (-1,-1), 10),
        ]))
        story.append(t_sign)

        doc.build(story)
        return filepath

