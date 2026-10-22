import os
from datetime import datetime
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from database import get_connection, EXPORTS_DIR
from services.audit_service import AuditService

class DevolucaoService:
    @staticmethod
    def get_employee_active_epis(funcionario_id: int) -> list:
        """
        Retorna os EPIs que o colaborador atualmente possui em mãos
        (Quantidade entregue em SAÍDA menos a quantidade já devolvida).
        Rastreia o tamanho exato de cada item sob custódia.
        """
        query = """
            SELECT m.epi_id, m.tamanho, e.codigo as epi_codigo, e.nome as epi_nome, e.ca as epi_ca,
                   e.unidade as epi_unidade, e.fabricante as epi_fabricante,
                   COALESCE(e.preco_unitario, 0.0) as epi_preco,
                   SUM(CASE WHEN m.tipo = 'SAIDA' THEN m.quantidade ELSE -m.quantidade END) as saldo_com_funcionario
            FROM movimentacoes m
            JOIN epis e ON e.id = m.epi_id
            WHERE m.funcionario_id = ?
            GROUP BY m.epi_id, m.tamanho
            HAVING saldo_com_funcionario > 0;
        """
        with get_connection() as conn:
            rows = conn.execute(query, (funcionario_id,)).fetchall()
            items = []
            for r in rows:
                item = dict(r)
                raw_t = (item.get("tamanho") or "Único").strip()
                if "," in raw_t:
                    item["tamanho"] = raw_t.split(",")[0].strip()
                item["epi_tamanho"] = item["tamanho"]
                items.append(item)
            return items

    @staticmethod
    def register_return(funcionario_id: int, items_returned: list, responsavel: str,
                        motivo: str, assinatura_path: str = None, obs: str = "") -> dict:
        """
        Registra a devolução de um ou mais EPIs pelo colaborador com validação de custódia ativa.
        items_returned: list de dicts com {'epi_id', 'quantidade', 'estado_conservacao', 'tamanho'}
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        mov_ids = []

        # Validação de segurança: verifica se o colaborador realmente possui esses itens em custódia
        active_epis = DevolucaoService.get_employee_active_epis(funcionario_id)
        active_map_exact = {(it["epi_id"], str(it.get("tamanho", "Único")).strip().upper()): it["saldo_com_funcionario"] for it in active_epis}
        active_map_general = {}
        for it in active_epis:
            active_map_general[it["epi_id"]] = active_map_general.get(it["epi_id"], 0) + it["saldo_com_funcionario"]

        itens_validos = []
        for it in items_returned:
            eid = it["epi_id"]
            tam_norm = str(it.get("tamanho", "Único")).strip().upper()
            saldo_disp = active_map_exact.get((eid, tam_norm), active_map_general.get(eid, 0))
            if saldo_disp <= 0:
                continue  # Item já devolvido anteriormente, ignora para não duplicar entrada
            qtd_solicitada = int(it["quantidade"])
            qtd_efetiva = min(qtd_solicitada, saldo_disp)
            if qtd_efetiva > 0:
                it_copy = dict(it)
                it_copy["quantidade"] = qtd_efetiva
                itens_validos.append(it_copy)

        if not itens_validos:
            raise ValueError("Nenhum item pendente de devolução foi encontrado na custódia deste colaborador. Os itens podem já ter sido devolvidos.")

        with get_connection() as conn:
            cursor = conn.cursor()
            for it in itens_validos:
                epi_id = it["epi_id"]
                qtd = int(it["quantidade"])
                estado = it.get("estado_conservacao", "Bom Estado")
                tamanho = it.get("tamanho", "Único")
                est_upper = str(estado).upper()

                # Busca preço do item caso não fornecido
                raw_preco = it.get("valor_unitario") or it.get("custo_unitario") or it.get("preco_unitario") or it.get("epi_preco")
                if raw_preco is not None and str(raw_preco).strip() != "":
                    try:
                        preco_unit = float(str(raw_preco).replace(",", "."))
                    except (ValueError, TypeError):
                        preco_unit = 0.0
                else:
                    cursor.execute("SELECT preco_unitario FROM epis WHERE id = ?;", (epi_id,))
                    p_row = cursor.fetchone()
                    preco_unit = float(p_row[0] or 0.0) if p_row else 0.0

                custo_total = round(preco_unit * qtd, 2)

                e_nao_devolvido = any(k in est_upper for k in ["NÃO DEVOLVIDO", "NAO DEVOLVIDO", "RETIDO", "EXTRAV"])
                retorna_ao_saldo = any(k in est_upper for k in ["BOM", "REUTIL", "HIGIEN"])
                e_ruim = any(k in est_upper for k in ["RUIM", "MANUT", "REPAR", "DESGASTE"])
                e_descarte = any(k in est_upper for k in ["DESC", "SUCATA", "INSERV", "IMPOSS", "DANIFICADO"]) and not e_nao_devolvido

                if e_nao_devolvido:
                    # Item não devolvido / retido: NÃO entra no estoque físico (nem bom, nem ruim, nem sucata)
                    tipo_mov = "NÃO DEVOLVIDO"
                else:
                    tipo_mov = "DEVOLUCAO"
                    if retorna_ao_saldo:
                        cursor.execute("UPDATE epis SET quantidade = quantidade + ?, qtd_usados_bons = qtd_usados_bons + ? WHERE id = ?;", (qtd, qtd, epi_id))
                        cursor.execute("""
                            INSERT INTO epi_grades (epi_id, tamanho, estado, quantidade, created_at)
                            VALUES (?, ?, 'BOM / REUTILIZÁVEL', ?, ?)
                            ON CONFLICT(epi_id, tamanho, estado) DO UPDATE SET quantidade = quantidade + ?;
                        """, (epi_id, tamanho, qtd, now, qtd))
                    elif e_ruim:
                        cursor.execute("UPDATE epis SET qtd_ruins = qtd_ruins + ? WHERE id = ?;", (qtd, epi_id))
                        cursor.execute("""
                            INSERT INTO epi_grades (epi_id, tamanho, estado, quantidade, created_at)
                            VALUES (?, ?, 'RUIM / REPARO', ?, ?)
                            ON CONFLICT(epi_id, tamanho, estado) DO UPDATE SET quantidade = quantidade + ?;
                        """, (epi_id, tamanho, qtd, now, qtd))
                    elif e_descarte:
                        cursor.execute("UPDATE epis SET qtd_descarte = qtd_descarte + ? WHERE id = ?;", (qtd, epi_id))
                        cursor.execute("""
                            INSERT INTO epi_grades (epi_id, tamanho, estado, quantidade, created_at)
                            VALUES (?, ?, 'DESCARTE / SUCATA', ?, ?)
                            ON CONFLICT(epi_id, tamanho, estado) DO UPDATE SET quantidade = quantidade + ?;
                        """, (epi_id, tamanho, qtd, now, qtd))

                cursor.execute("""
                    INSERT INTO movimentacoes (
                        tipo, epi_id, funcionario_id, quantidade, custo_unitario, custo_total,
                        data_hora, responsavel_entrega, motivo, assinatura_path, estado_conservacao,
                        tamanho, observacao, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (tipo_mov, epi_id, funcionario_id, qtd, preco_unit, custo_total, now, responsavel, motivo, assinatura_path, estado, tamanho, obs, now))
                mov_ids.append(cursor.lastrowid)

            conn.commit()

        AuditService.log(
            acao="DEVOLUCAO_EPI",
            modulo="MOVIMENTACOES",
            detalhes=f"Devolução de {len(items_returned)} item(ns) pelo Colaborador ID {funcionario_id}. Motivo: {motivo} ({responsavel})"
        )

        try:
            from ui.views.tv_mode_view import TVModeWindow
            TVModeWindow.trigger_instant_refresh()
        except Exception:
            pass

        return {"sucesso": True, "mov_ids": mov_ids}

    @staticmethod
    def generate_termo_devolucao_pdf(funcionario_id: int, items_returned: list,
                                     responsavel: str, motivo: str,
                                     assinatura_colaborador_path: str = None) -> str:
        """
        Gera o Termo Oficial de Devolução e Quitação de EPIs em PDF formato A4 Paisagem.
        """
        os.makedirs(EXPORTS_DIR, exist_ok=True)

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM funcionarios WHERE id = ?;", (funcionario_id,))
            row = cursor.fetchone()
            func = dict(row) if row else {
                "id": funcionario_id,
                "matricula": f"FUNC_{funcionario_id}",
                "nome": "Colaborador",
                "cpf": "-",
                "cargo": "-",
                "departamento": "-"
            }

            cfg_rows = cursor.execute("SELECT chave, valor FROM configuracoes;").fetchall()
            configs = {r["chave"]: r["valor"] for r in cfg_rows}

        empresa_nome = configs.get("empresa_nome", "EMPRESA INDUSTRIAL LTDA")
        empresa_cnpj = configs.get("empresa_cnpj", "00.000.000/0001-00")
        termo_texto = configs.get("termo_devolucao", (
            "Declaro para os devidos fins que procedi à devolução dos Equipamentos de Proteção Individual (EPIs) "
            "acima descritos, no estado de conservação indicado, dando à empresa plena e rasa quitação quanto à posse "
            "e guarda dos mesmos, nos termos da NR-6 e da legislação trabalhista vigente."
        ))

        safe_matr = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in str(func.get("matricula") or func.get("id") or funcionario_id))
        filename = f"Termo_Devolucao_{safe_matr}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = os.path.join(EXPORTS_DIR, filename)

        doc = SimpleDocTemplate(
            filepath,
            pagesize=landscape(A4),
            rightMargin=20,
            leftMargin=20,
            topMargin=20,
            bottomMargin=20
        )

        styles = getSampleStyleSheet()
        style_title = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=13,
            textColor=colors.HexColor("#1E3A8A"),
            alignment=1,
            spaceAfter=3
        )
        style_sub = ParagraphStyle(
            "DocSub",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            textColor=colors.HexColor("#475569"),
            alignment=1,
            spaceAfter=10
        )
        style_term = ParagraphStyle(
            "TermStyle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#1E293B"),
            alignment=4
        )
        cell_style = ParagraphStyle(
            "CellNormal",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10
        )
        cell_center = ParagraphStyle(
            "CellCenter",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            alignment=1
        )
        cell_right = ParagraphStyle(
            "CellRight",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            alignment=2
        )
        th_style = ParagraphStyle(
            "THStyle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.white,
            alignment=1
        )
        cell_bold = ParagraphStyle(
            "CellBold",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10
        )

        def _parse_estado_destinacao(raw_estado):
            s = str(raw_estado or "").upper()
            if any(k in s for k in ["BOM", "REUTIL", "HIGIEN"]):
                return "Bom / Reutilizável", "Retorno ao Estoque"
            elif any(k in s for k in ["RUIM", "MANUT", "REPAR", "DESGASTE"]):
                return "Ruim (Necessita Manut.)", "Avaliação / Reparo"
            elif any(k in s for k in ["DESC", "SUCATA", "INSERV", "IMPOSS", "DANIFICADO"]):
                return "Inservível / Sucata", "Descarte / Baixa"
            elif any(k in s for k in ["NÃO DEVOLVIDO", "NAO DEVOLVIDO", "RETIDO", "EXTRAV"]):
                return "Não Devolvido / Retido", "Cobrança / TRCT"
            else:
                return "Bom / Reutilizável", "Retorno ao Estoque"

        story = []

        # Cabeçalho
        story.append(Paragraph(f"<b>{empresa_nome.upper()}</b>", style_title))
        story.append(Paragraph(f"CNPJ: {empresa_cnpj} &nbsp;|&nbsp; <b>TERMO DE DEVOLUÇÃO E QUITAÇÃO DE EPIs (NR-6 / CLT)</b>", style_sub))

        # Quadro do Funcionário
        info_data = [
            [
                Paragraph(f"<b>Colaborador:</b> {func['nome']}", cell_style),
                Paragraph(f"<b>Matrícula:</b> {func['matricula']}", cell_style),
                Paragraph(f"<b>CPF:</b> {func.get('cpf') or '-'}", cell_style),
            ],
            [
                Paragraph(f"<b>Função / Cargo:</b> {func['cargo']}", cell_style),
                Paragraph(f"<b>Departamento:</b> {func['departamento']}", cell_style),
                Paragraph(f"<b>Motivo:</b> {motivo}", cell_style),
            ]
        ]
        info_table = Table(info_data, colWidths=[320, 220, 260])
        info_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 10))

        # Tabela de EPIs Devolvidos
        headers = [
            Paragraph("CÓDIGO", th_style),
            Paragraph("EQUIPAMENTO (EPI)", th_style),
            Paragraph("TAM.", th_style),
            Paragraph("C.A.", th_style),
            Paragraph("QTD", th_style),
            Paragraph("VALOR UNIT.", th_style),
            Paragraph("TOTAL R$", th_style),
            Paragraph("ESTADO DE CONSERVAÇÃO", th_style),
            Paragraph("DESTINAÇÃO", th_style)
        ]
        rows = [headers]
        total_financeiro_devolucao = 0.0

        for it in items_returned:
            est_lbl, dest_lbl = _parse_estado_destinacao(it.get("estado_conservacao"))
            tam_str = str(it.get("tamanho") or it.get("epi_tamanho") or "Único").strip()
            if "," in tam_str:
                tam_str = tam_str.split(",")[0].strip()
            if tam_str.upper() in ("ÚNICO", "UNICO", "-"):
                tam_str = "-"

            raw_p = it.get("valor_unitario") or it.get("custo_unitario") or it.get("preco_unitario") or it.get("epi_preco") or 0.0
            try:
                p_unit = float(str(raw_p).replace(",", "."))
            except (ValueError, TypeError):
                p_unit = 0.0

            qtd_it = int(it.get('quantidade', 1))
            subtot_it = round(qtd_it * p_unit, 2)
            total_financeiro_devolucao += subtot_it

            val_unit_str = f"R$ {p_unit:.2f}" if p_unit > 0 else "-"
            val_tot_str = f"R$ {subtot_it:.2f}" if subtot_it > 0 else "-"

            rows.append([
                Paragraph(str(it.get("epi_codigo", "")), cell_center),
                Paragraph(str(it.get("epi_nome", "")), cell_style),
                Paragraph(tam_str, cell_center),
                Paragraph(str(it.get("epi_ca", "") or "-"), cell_center),
                Paragraph(f"<b>{qtd_it}</b> {it.get('epi_unidade', 'UN')}", cell_center),
                Paragraph(val_unit_str, cell_right),
                Paragraph(f"<b>{val_tot_str}</b>", cell_right),
                Paragraph(est_lbl, cell_center),
                Paragraph(dest_lbl, cell_center)
            ])

        # Linha de total financeiro
        if total_financeiro_devolucao > 0:
            rows.append([
                Paragraph("<b>TOTAL GERAL:</b>", cell_bold),
                Paragraph(f"<b>{len(items_returned)} item(ns) listado(s)</b>", cell_style),
                Paragraph("", cell_center),
                Paragraph("", cell_center),
                Paragraph("", cell_center),
                Paragraph("<b>Subtotal:</b>", cell_right),
                Paragraph(f"<b>R$ {total_financeiro_devolucao:.2f}</b>", cell_right),
                Paragraph("", cell_center),
                Paragraph("", cell_center)
            ])

        col_w = [55, 230, 45, 50, 50, 70, 75, 115, 110]
        tbl_epis = Table(rows, colWidths=col_w)
        tbl_epis.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(tbl_epis)
        story.append(Spacer(1, 10))

        # Termo de Compromisso e Quitação
        story.append(Paragraph(f"<b>TERMO DE QUITAÇÃO:</b> {termo_texto}", style_term))
        story.append(Spacer(1, 15))

        # Assinaturas Lado a Lado
        dt_hoje = datetime.now().strftime("%d de %B de %Y")
        colab_sig_elements = []
        if assinatura_colaborador_path and os.path.exists(assinatura_colaborador_path):
            try:
                colab_sig_elements.append(Image(assinatura_colaborador_path, width=130, height=38))
            except Exception:
                colab_sig_elements.append(Spacer(1, 38))
        else:
            colab_sig_elements.append(Spacer(1, 38))
        colab_sig_elements.append(Paragraph(f"____________________________________________<br/><b>{func['nome']}</b><br/>Assinatura do Colaborador", cell_style))

        resp_sig_elements = [
            Spacer(1, 38),
            Paragraph(f"____________________________________________<br/><b>{responsavel}</b><br/>Almoxarifado / Segurança do Trabalho", cell_style)
        ]

        sig_table = Table([[colab_sig_elements, resp_sig_elements]], colWidths=[400, 400])
        sig_table.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ]))
        story.append(KeepTogether(sig_table))

        doc.build(story)
        return filepath

    @staticmethod
    def register_unreturned_dismissal(funcionario_id: int, items_unreturned: list,
                                     responsavel: str, motivo: str = "Demissão sem Devolução de EPI (Ausência / Recusa)",
                                     obs: str = "", alterar_status_funcionario: bool = True) -> dict:
        """
        Registra a NÃO devolução de EPIs na demissão (extravio/retenção indevida).
        Calcula o prejuízo financeiro total para instrução de desconto em rescisão (TRCT - CLT art. 462).
        NÃO devolve os itens ao estoque físico (fica em falta).
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        mov_ids = []
        total_prejuizo = 0.0

        with get_connection() as conn:
            cursor = conn.cursor()

            for it in items_unreturned:
                epi_id = it["epi_id"]
                qtd = int(it["quantidade"])
                
                # Busca preço unitário oficial do EPI
                cursor.execute("SELECT preco_unitario, nome, codigo FROM epis WHERE id = ?;", (epi_id,))
                epi_row = cursor.fetchone()
                preco_unit = float(epi_row["preco_unitario"] or 0.0) if epi_row else 0.0
                custo_total = qtd * preco_unit
                total_prejuizo += custo_total

                # Insere movimentação de EXTRAVIO_DEMISSAO
                cursor.execute("""
                    INSERT INTO movimentacoes (
                        tipo, epi_id, funcionario_id, quantidade, custo_unitario, custo_total,
                        data_hora, responsavel_entrega, motivo, assinatura_path, estado_conservacao,
                        observacao, created_at
                    ) VALUES ('EXTRAVIO_DEMISSAO', ?, ?, ?, ?, ?, ?, ?, ?, NULL, 'Não Devolvido / Retido na Demissão', ?, ?);
                """, (epi_id, funcionario_id, qtd, preco_unit, custo_total, now, responsavel, motivo, obs, now))
                mov_ids.append(cursor.lastrowid)

            # Atualiza o status do colaborador para Desligado com Pendência
            if alterar_status_funcionario:
                cursor.execute("""
                    UPDATE funcionarios
                    SET status = 'Desligado (Com Pendência de EPI)'
                    WHERE id = ?;
                """, (funcionario_id,))

            conn.commit()

        AuditService.log(
            acao="EXTRAVIO_DEMISSAO",
            modulo="MOVIMENTACOES",
            detalhes=f"Registrada NÃO devolução na demissão de {len(items_unreturned)} item(ns) pelo Colaborador ID {funcionario_id}. Prejuízo apurado: R$ {total_prejuizo:.2f}. Registrado por: {responsavel}"
        )

        try:
            from ui.views.tv_mode_view import TVModeWindow
            TVModeWindow.trigger_instant_refresh()
        except Exception:
            pass

        return {
            "sucesso": True,
            "mov_ids": mov_ids,
            "total_prejuizo": total_prejuizo
        }

    @staticmethod
    def generate_termo_nao_devolucao_pdf(funcionario_id: int, items_unreturned: list,
                                        responsavel: str, motivo: str, total_prejuizo: float,
                                        obs: str = "") -> str:
        """
        Gera o Termo Oficial de Constatação de Não Devolução e Extravio de EPIs para o RH/TRCT.
        Documento com valor jurídico formal nos termos do art. 462 § 1º da CLT e NR-6.
        """
        os.makedirs(EXPORTS_DIR, exist_ok=True)

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM funcionarios WHERE id = ?;", (funcionario_id,))
            row = cursor.fetchone()
            func = dict(row) if row else {
                "id": funcionario_id,
                "matricula": f"FUNC_{funcionario_id}",
                "nome": "Colaborador",
                "cpf": "-",
                "cargo": "-",
                "departamento": "-"
            }

            cfg_rows = cursor.execute("SELECT chave, valor FROM configuracoes;").fetchall()
            configs = {r["chave"]: r["valor"] for r in cfg_rows}

        empresa_nome = configs.get("empresa_nome", "EMPRESA INDUSTRIAL LTDA")
        empresa_cnpj = configs.get("empresa_cnpj", "00.000.000/0001-00")
        empresa_end = configs.get("empresa_endereco", "")

        safe_matr = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in str(func.get("matricula") or func.get("id") or funcionario_id))
        filename = f"Termo_Nao_Devolucao_{safe_matr}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = os.path.join(EXPORTS_DIR, filename)

        doc = SimpleDocTemplate(
            filepath,
            pagesize=landscape(A4),
            rightMargin=20,
            leftMargin=20,
            topMargin=20,
            bottomMargin=20
        )

        styles = getSampleStyleSheet()
        style_title = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=13,
            textColor=colors.HexColor("#DC2626"),
            alignment=1,
            spaceAfter=2
        )
        style_sub = ParagraphStyle(
            "DocSub",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            textColor=colors.HexColor("#1E293B"),
            alignment=1,
            spaceAfter=8
        )
        style_juridico = ParagraphStyle(
            "LegalText",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#1E293B"),
            alignment=4
        )
        cell_style = ParagraphStyle(
            "CellNormalRed",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10
        )
        cell_center = ParagraphStyle(
            "CellCenterRed",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            alignment=1
        )
        cell_right = ParagraphStyle(
            "CellRightRed",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            alignment=2
        )
        th_style = ParagraphStyle(
            "THStyleRed",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.white,
            alignment=1
        )

        story = []

        # Cabeçalho Oficial
        story.append(Paragraph(f"<b>{empresa_nome.upper()}</b>", style_title))
        story.append(Paragraph(f"CNPJ: {empresa_cnpj} &nbsp;|&nbsp; {empresa_end}", style_sub))
        story.append(Paragraph("<b>TERMO DE CONSTATAÇÃO DE NÃO DEVOLUÇÃO E EXTRAVIO DE EPIs NA RESCISÃO CONTRATUAL</b>", ParagraphStyle(
            "DocHeader", fontName="Helvetica-Bold", fontSize=11, textColor=colors.HexColor("#991B1B"), alignment=1, spaceAfter=8
        )))

        # Quadro do Funcionário
        dt_hoje = datetime.now().strftime("%d/%m/%Y %H:%M")
        info_data = [
            [
                Paragraph(f"<b>Ex-Colaborador:</b> {func['nome']}", cell_style),
                Paragraph(f"<b>Matrícula:</b> {func['matricula']}", cell_style),
                Paragraph(f"<b>CPF:</b> {func.get('cpf') or '-'}", cell_style),
            ],
            [
                Paragraph(f"<b>Função / Cargo:</b> {func['cargo']}", cell_style),
                Paragraph(f"<b>Departamento / Setor:</b> {func['departamento']}", cell_style),
                Paragraph(f"<b>Data da Constatação:</b> {dt_hoje}", cell_style),
            ],
            [
                Paragraph(f"<b>Motivo Registrado:</b> {motivo}", cell_style),
                Paragraph(f"<b>Status Atual:</b> Desligado / Em Falta de EPIs", cell_style),
                Paragraph(f"<b>Registrado por:</b> {responsavel}", cell_style),
            ]
        ]
        info_table = Table(info_data, colWidths=[310, 240, 250])
        info_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FEF2F2")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#FCA5A5")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#FECACA")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 8))

        # Tabela de EPIs Retidos / Não Devolvidos com Valores
        headers = [
            Paragraph("CÓDIGO", th_style),
            Paragraph("EQUIPAMENTO (EPI RETIDO)", th_style),
            Paragraph("C.A.", th_style),
            Paragraph("QUANTIDADE", th_style),
            Paragraph("VALOR UNITÁRIO", th_style),
            Paragraph("PREJUÍZO TOTAL", th_style)
        ]
        rows = [headers]

        for it in items_unreturned:
            qtd = int(it.get("quantidade", 1))
            preco_u = float(it.get("epi_preco", 0.0) or 0.0)
            subtot = qtd * preco_u
            rows.append([
                Paragraph(str(it.get("epi_codigo", "")), cell_center),
                Paragraph(str(it.get("epi_nome", "")), cell_style),
                Paragraph(str(it.get("epi_ca", "") or "-"), cell_center),
                Paragraph(f"<b>{qtd}</b> {it.get('epi_unidade', 'UN')}", cell_center),
                Paragraph(f"R$ {preco_u:.2f}", cell_right),
                Paragraph(f"<b>R$ {subtot:.2f}</b>", cell_right)
            ])

        col_w = [70, 330, 70, 80, 125, 125]
        tbl_epis = Table(rows, colWidths=col_w)
        tbl_epis.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#991B1B")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FFF1F2")]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(tbl_epis)
        story.append(Spacer(1, 6))

        # Quadro de Destaque Financeiro
        resumo_data = [[
            Paragraph("<b>STATUS: EQUIPAMENTOS EM FALTA NO ALMOXARIFADO (NÃO RESTITUÍDOS NA RESCISÃO)</b>", ParagraphStyle("ResTxt", fontName="Helvetica-Bold", fontSize=9, textColor=colors.HexColor("#991B1B"))),
            Paragraph(f"<b>TOTAL A RESSARCIR / DESCONTAR (TRCT): R$ {total_prejuizo:.2f}</b>", ParagraphStyle("ValTxt", fontName="Helvetica-Bold", fontSize=10, textColor=colors.HexColor("#991B1B"), alignment=2))
        ]]
        tbl_resumo = Table(resumo_data, colWidths=[480, 320])
        tbl_resumo.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FEE2E2")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#EF4444")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ]))
        story.append(tbl_resumo)
        story.append(Spacer(1, 8))

        # Texto Legal Fundamentado na CLT e NR-6
        texto_juridico = (
            "<b>FUNDAMENTAÇÃO JURÍDICA E FINALIDADE:</b><br/>"
            "Certificamos para todos os fins de direito e instrução do Termo de Rescisão do Contrato de Trabalho (TRCT) que o colaborador acima qualificado, "
            "por ocasião do término de seu vínculo laboral com a empresa, <b>NÃO compareceu ao almoxarifado ou recusou-se a devolver</b> os Equipamentos de Proteção "
            "Individual (EPIs) de propriedade da empresa que se encontravam sob sua posse, guarda e responsabilidade, conforme Cautela firmada nos termos "
            "do Art. 166 da Consolidação das Leis do Trabalho (CLT) e da Norma Regulamentadora NR-6 do Ministério do Trabalho e Emprego.<br/><br/>"
            "Diante do descumprimento injustificado do dever legal e contratual de restituição dos bens materiais de titularidade da empregadora, "
            "fica lavrado o presente Termo com a apuração do prejuízo financeiro direto suportado pela empresa, servindo como documento hábil comprobatório "
            "para fins de compensação/desconto na rescisão contratual, com fulcro no <b>Art. 462, § 1º, da CLT</b>, e/ou para a adoção das medidas cíveis e criminais cabíveis."
        )
        if obs:
            texto_juridico += f"<br/><br/><b>Observações Adicionais:</b> {obs}"

        story.append(Paragraph(texto_juridico, style_juridico))
        story.append(Spacer(1, 15))

        # Quadro de Assinaturas (Almoxarifado, RH e Testemunhas)
        sig_data = [
            [
                Paragraph("____________________________________________<br/><b>Almoxarifado / Segurança do Trabalho</b><br/>Responsável pela Conferência", cell_style),
                Paragraph("____________________________________________<br/><b>Recursos Humanos / Departamento Pessoal</b><br/>Ciência e Instrução do TRCT", cell_style),
                Paragraph("____________________________________________<br/><b>Testemunha 1</b><br/>Nome / CPF:", cell_style),
                Paragraph("____________________________________________<br/><b>Testemunha 2</b><br/>Nome / CPF:", cell_style),
            ]
        ]
        sig_tbl = Table(sig_data, colWidths=[200, 200, 200, 200])
        sig_tbl.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ]))
        story.append(KeepTogether(sig_tbl))

        doc.build(story)
        return filepath

