from database import get_connection
from datetime import datetime, timedelta

class MovementService:
    @staticmethod
    def normalize_date_iso(val):
        """
        Converte com segurança qualquer entrada de data (brasileira ou ISO) para 'YYYY-MM-DD'.
        Exemplos aceitos: '18/10/2026', '18-10-2026', '18.10.2026', '18/10', '2026-10-18', '2026/10/18'.
        Retorna 'YYYY-MM-DD' ou None se vazio/inválido.
        """
        if not val:
            return None
        val_str = str(val).strip()
        if not val_str:
            return None

        clean = val_str.replace(".", "/").replace("-", "/").strip()
        if " " in clean:
            clean = clean.split(" ")[0].strip()

        parts = [p.strip() for p in clean.split("/") if p.strip()]
        if len(parts) == 2:
            clean = f"{parts[0]}/{parts[1]}/{datetime.now().year}"

        for fmt in ("%d/%m/%Y", "%Y/%m/%d", "%d/%m/%y"):
            try:
                return datetime.strptime(clean, fmt).strftime("%Y-%m-%d")
            except ValueError:
                pass

        digits = "".join(c for c in val_str if c.isdigit())
        if len(digits) == 8:
            if 1990 <= int(digits[:4]) <= 2099:
                try:
                    return datetime.strptime(digits, "%Y%m%d").strftime("%Y-%m-%d")
                except ValueError:
                    pass
            try:
                return datetime.strptime(digits, "%d%m%Y").strftime("%Y-%m-%d")
            except ValueError:
                pass

        return None

    @staticmethod
    def parse_date(date_str):
        """Converte strings em formatos comuns (DD/MM/AAAA ou AAAA-MM-DD) para AAAA-MM-DD HH:MM:SS."""
        if not date_str:
            return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        dt = str(date_str).strip()
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%d/%m/%Y %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%d/%m/%Y %H:%M",
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%d.%m.%Y",
            "%Y/%m/%d"
        ]
        for fmt in formats:
            try:
                parsed = datetime.strptime(dt, fmt)
                if fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y/%m/%d"):
                    return parsed.strftime("%Y-%m-%d 08:00:00")
                return parsed.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                pass

        # Tenta fallback via normalizador
        norm = MovementService.normalize_date_iso(dt)
        if norm:
            return f"{norm} 08:00:00"

        raise ValueError(f"Formato de data inválido: '{date_str}'. Formatos aceitos: DD/MM/AAAA ou AAAA-MM-DD (ex: 15/03/2023 ou 2023-03-15).")

    @staticmethod
    def register_exit(epi_id, funcionario_id, quantidade, responsavel_entrega, motivo,
                      data_hora=None, observacao="", assinatura_path=None, foto_path=None,
                      is_retroativo=False, descontar_estoque=True, tamanho=None, estado_conservacao="NOVO",
                      custo_unitario=None):
        """
        Registra uma saída de EPI para um funcionário com rastreio de tamanho, custo unitário e estado de conservação (Novo ou Reutilizado).
        """
        if not responsavel_entrega or not responsavel_entrega.strip():
            raise ValueError("O nome do responsável pela entrega é obrigatório!")

        if quantidade <= 0:
            raise ValueError("A quantidade deve ser maior que zero!")

        data_hora = MovementService.parse_date(data_hora)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        estado_conservacao = (estado_conservacao or "NOVO").strip().upper()
        tamanho = (tamanho or "Único").strip()

        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT quantidade, nome, preco_unitario, qtd_novos, qtd_usados_bons FROM epis WHERE id = ? AND ativo = 1", (epi_id,))
            epi = cursor.fetchone()
            if not epi:
                raise ValueError("EPI não encontrado ou inativo no sistema.")

            estoque_atual = epi["quantidade"]
            if descontar_estoque:
                if estoque_atual < quantidade and not is_retroativo:
                    raise ValueError(f"Saldo insuficiente! Saldo atual de '{epi['nome']}': {estoque_atual} unid. Solicitado: {quantidade} unid.")

                nova_qtd = max(0, estoque_atual - quantidade) if is_retroativo else (estoque_atual - quantidade)

                if "NOVO" in estado_conservacao:
                    cursor.execute("UPDATE epis SET quantidade = ?, qtd_novos = MAX(0, qtd_novos - ?) WHERE id = ?",
                                   (nova_qtd, quantidade, epi_id))
                else:
                    cursor.execute("UPDATE epis SET quantidade = ?, qtd_usados_bons = MAX(0, qtd_usados_bons - ?) WHERE id = ?",
                                   (nova_qtd, quantidade, epi_id))

                # Atualiza também na tabela epi_grades
                cursor.execute("""
                    UPDATE epi_grades
                    SET quantidade = MAX(0, quantidade - ?)
                    WHERE epi_id = ? AND UPPER(tamanho) = UPPER(?) AND UPPER(estado) LIKE ?;
                """, (quantidade, epi_id, tamanho, f"%{estado_conservacao[:4]}%"))

            if custo_unitario is not None:
                preco_unit = float(custo_unitario)
            else:
                p_base = float(epi["preco_unitario"] or 0.0)
                if any(k in estado_conservacao for k in ["REUTIL", "USADO", "BOM", "HIGIEN"]):
                    preco_unit = round(p_base * 0.5, 2)
                else:
                    preco_unit = p_base
            custo_tot = round(quantidade * preco_unit, 2)

            obs_final = observacao.strip() if observacao else ""
            if is_retroativo and "[Lançamento Retroativo]" not in obs_final:
                obs_final = f"[Lançamento Retroativo - Data: {data_hora[:10]}] {obs_final}".strip()

            cursor.execute("""
                INSERT INTO movimentacoes (tipo, epi_id, funcionario_id, quantidade,
                                          custo_unitario, custo_total, data_hora, responsavel_entrega,
                                          motivo, assinatura_path, foto_path, observacao, tamanho,
                                          estado_conservacao, created_at)
                VALUES ('SAIDA', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                epi_id,
                funcionario_id,
                quantidade,
                preco_unit,
                custo_tot,
                data_hora,
                responsavel_entrega.strip(),
                motivo.strip(),
                assinatura_path,
                foto_path,
                obs_final,
                tamanho,
                estado_conservacao,
                now
            ))
            last_id = cursor.lastrowid

            cursor.execute("""
                INSERT OR IGNORE INTO operadores (nome, cargo)
                VALUES (?, 'Operador Almoxarifado')
            """, (responsavel_entrega.strip(),))

            conn.commit()

            try:
                from services.audit_service import AuditService
                AuditService.log(
                    acao="SAIDA_EPI",
                    modulo="MOVIMENTACOES",
                    detalhes=f"Saída de {quantidade} un de '{epi['nome']}' (R$ {custo_tot:.2f}) para Func ID {funcionario_id}. Entregador: {responsavel_entrega.strip()}"
                )
            except Exception:
                pass

            try:
                from ui.views.tv_mode_view import TVModeWindow
                TVModeWindow.trigger_instant_refresh()
            except Exception:
                pass

            return last_id

    @staticmethod
    def get_top_epis_consumed(limit=5):
        """Retorna os EPIs com maior volume de saídas para alimentação dos gráficos."""
        with get_connection() as conn:
            rows = conn.execute("""
                SELECT e.nome, SUM(m.quantidade) as total_qtd, 
                       SUM(CASE 
                           WHEN (m.custo_total IS NOT NULL AND m.custo_total > 0.0) THEN m.custo_total
                           WHEN (m.custo_unitario IS NOT NULL AND m.custo_unitario > 0.0) THEN m.quantidade * m.custo_unitario
                           WHEN UPPER(COALESCE(m.estado_conservacao, '')) LIKE '%USADO%' 
                             OR UPPER(COALESCE(m.estado_conservacao, '')) LIKE '%REUTIL%' 
                             OR UPPER(COALESCE(m.estado_conservacao, '')) LIKE '%BOM%' 
                           THEN m.quantidade * COALESCE(NULLIF(e.preco_usado, 0.0), e.preco_unitario * 0.5, 0.0)
                           ELSE m.quantidade * COALESCE(e.preco_unitario, 0.0)
                       END) as total_valor
                FROM movimentacoes m
                JOIN epis e ON m.epi_id = e.id
                WHERE m.tipo = 'SAIDA'
                GROUP BY m.epi_id
                ORDER BY total_qtd DESC
                LIMIT ?;
            """, (limit,)).fetchall()
            return [
                {
                    "label": r["nome"],
                    "value": r["total_qtd"],
                    "formatted": f"{r['total_qtd']} un (R$ {r['total_valor']:.2f})"
                }
                for r in rows
            ]

    @staticmethod
    def get_department_costs(limit=5):
        """Retorna gastos acumulados por departamento para os gráficos."""
        with get_connection() as conn:
            rows = conn.execute("""
                SELECT f.departamento, 
                       SUM(CASE 
                           WHEN (m.custo_total IS NOT NULL AND m.custo_total > 0.0) THEN m.custo_total
                           WHEN (m.custo_unitario IS NOT NULL AND m.custo_unitario > 0.0) THEN m.quantidade * m.custo_unitario
                           WHEN UPPER(COALESCE(m.estado_conservacao, '')) LIKE '%USADO%' 
                             OR UPPER(COALESCE(m.estado_conservacao, '')) LIKE '%REUTIL%' 
                             OR UPPER(COALESCE(m.estado_conservacao, '')) LIKE '%BOM%' 
                           THEN m.quantidade * COALESCE(NULLIF(e.preco_usado, 0.0), e.preco_unitario * 0.5, 0.0)
                           ELSE m.quantidade * COALESCE(e.preco_unitario, 0.0)
                       END) as total_custo, 
                       SUM(m.quantidade) as total_qtd
                FROM movimentacoes m
                JOIN epis e ON m.epi_id = e.id
                JOIN funcionarios f ON m.funcionario_id = f.id
                WHERE m.tipo = 'SAIDA'
                GROUP BY f.departamento
                ORDER BY total_custo DESC
                LIMIT ?;
            """, (limit,)).fetchall()
            return [
                {
                    "label": r["departamento"],
                    "value": round(r["total_custo"], 2),
                    "formatted": f"R$ {r['total_custo']:.2f} ({r['total_qtd']} un)"
                }
                for r in rows
            ]

    @staticmethod
    def register_entry(epi_id, quantidade, responsavel, motivo="Compra / Reposição de Estoque", data_hora=None, observacao="", custo_unitario=None, tamanho="Único", estado_conservacao="NOVO", atualizar_preco_base=False):
        """Registra entrada no estoque com valor de custo, tamanho e estado de conservação."""
        if not responsavel or not responsavel.strip():
            raise ValueError("O nome do responsável pela entrada é obrigatório!")

        if quantidade <= 0:
            raise ValueError("A quantidade deve ser maior que zero!")

        data_hora = MovementService.parse_date(data_hora)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        estado_conservacao = (estado_conservacao or "NOVO").strip().upper()
        tamanho = (tamanho or "Único").strip()

        with get_connection() as conn:
            cursor = conn.cursor()

            if custo_unitario is None:
                epi = cursor.execute("SELECT preco_unitario FROM epis WHERE id = ?", (epi_id,)).fetchone()
                custo_unitario = float(epi["preco_unitario"] or 0.0) if epi else 0.0
            else:
                try:
                    custo_unitario = float(str(custo_unitario).replace(",", "."))
                except (ValueError, TypeError):
                    custo_unitario = 0.0

            if atualizar_preco_base and custo_unitario > 0:
                cursor.execute("UPDATE epis SET preco_unitario = ? WHERE id = ?", (custo_unitario, epi_id))

            custo_total = quantidade * custo_unitario

            # Atualiza epis
            if "NOVO" in estado_conservacao:
                cursor.execute("UPDATE epis SET quantidade = quantidade + ?, qtd_novos = qtd_novos + ? WHERE id = ?", (quantidade, quantidade, epi_id))
            elif "BOM" in estado_conservacao or "REUTIL" in estado_conservacao:
                cursor.execute("UPDATE epis SET quantidade = quantidade + ?, qtd_usados_bons = qtd_usados_bons + ? WHERE id = ?", (quantidade, quantidade, epi_id))
            elif "RUIM" in estado_conservacao or "MANUT" in estado_conservacao:
                cursor.execute("UPDATE epis SET qtd_ruins = qtd_ruins + ? WHERE id = ?", (quantidade, epi_id))
            else:
                cursor.execute("UPDATE epis SET qtd_descarte = qtd_descarte + ? WHERE id = ?", (quantidade, epi_id))

            # Atualiza epi_grades
            est_grade = "NOVO" if "NOVO" in estado_conservacao else ("BOM / REUTILIZÁVEL" if "BOM" in estado_conservacao or "REUTIL" in estado_conservacao else ("RUIM / REPARO" if "RUIM" in estado_conservacao else "DESCARTE / SUCATA"))
            cursor.execute("""
                INSERT INTO epi_grades (epi_id, tamanho, estado, quantidade, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(epi_id, tamanho, estado) DO UPDATE SET quantidade = quantidade + ?;
            """, (epi_id, tamanho, est_grade, quantidade, now, quantidade))

            cursor.execute("""
                INSERT INTO movimentacoes (tipo, epi_id, funcionario_id, quantidade,
                                          custo_unitario, custo_total, data_hora, responsavel_entrega,
                                          motivo, observacao, tamanho, estado_conservacao, created_at)
                VALUES ('ENTRADA', ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                epi_id,
                quantidade,
                custo_unitario,
                custo_total,
                data_hora,
                responsavel.strip(),
                motivo.strip(),
                observacao.strip() if observacao else "",
                tamanho,
                estado_conservacao,
                now
            ))
            last_id = cursor.lastrowid
            conn.commit()

            try:
                from ui.views.tv_mode_view import TVModeWindow
                TVModeWindow.trigger_instant_refresh()
            except Exception:
                pass

            return last_id

    @staticmethod
    def register_return(epi_id, funcionario_id, quantidade, responsavel, motivo="Devolução / Troca", data_hora=None, observacao="", tamanho="Único", estado_conservacao="BOM / REUTILIZÁVEL"):
        """Registra a devolução de um EPI com rastreio de estado de conservação (Bom, Ruim ou Descarte)."""
        if not responsavel or not responsavel.strip():
            raise ValueError("O nome do responsável pelo recebimento é obrigatório!")

        if quantidade <= 0:
            raise ValueError("A quantidade deve ser maior que zero!")

        if not data_hora:
            data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        estado_conservacao = (estado_conservacao or "BOM / REUTILIZÁVEL").strip()
        tamanho = (tamanho or "Único").strip()
        est_upper = estado_conservacao.upper()

        with get_connection() as conn:
            cursor = conn.cursor()

            # Se for bom/reutilizável, retorna ao saldo físico útil
            retorna_saldo = any(k in est_upper for k in ["BOM", "REUTIL", "HIGIEN"])
            e_ruim = any(k in est_upper for k in ["RUIM", "MANUT", "REPAR", "DESGASTE"])
            e_descarte = any(k in est_upper for k in ["DESC", "SUCATA", "INSERV", "IMPOSS", "DANIFICADO"])

            if retorna_saldo:
                cursor.execute("UPDATE epis SET quantidade = quantidade + ?, qtd_usados_bons = qtd_usados_bons + ? WHERE id = ?", (quantidade, quantidade, epi_id))
                cursor.execute("""
                    INSERT INTO epi_grades (epi_id, tamanho, estado, quantidade, created_at)
                    VALUES (?, ?, 'BOM / REUTILIZÁVEL', ?, ?)
                    ON CONFLICT(epi_id, tamanho, estado) DO UPDATE SET quantidade = quantidade + ?;
                """, (epi_id, tamanho, quantidade, now, quantidade))
            elif e_ruim:
                cursor.execute("UPDATE epis SET qtd_ruins = qtd_ruins + ? WHERE id = ?", (quantidade, epi_id))
                cursor.execute("""
                    INSERT INTO epi_grades (epi_id, tamanho, estado, quantidade, created_at)
                    VALUES (?, ?, 'RUIM / REPARO', ?, ?)
                    ON CONFLICT(epi_id, tamanho, estado) DO UPDATE SET quantidade = quantidade + ?;
                """, (epi_id, tamanho, quantidade, now, quantidade))
            elif e_descarte:
                cursor.execute("UPDATE epis SET qtd_descarte = qtd_descarte + ? WHERE id = ?", (quantidade, epi_id))
                cursor.execute("""
                    INSERT INTO epi_grades (epi_id, tamanho, estado, quantidade, created_at)
                    VALUES (?, ?, 'DESCARTE / SUCATA', ?, ?)
                    ON CONFLICT(epi_id, tamanho, estado) DO UPDATE SET quantidade = quantidade + ?;
                """, (epi_id, tamanho, quantidade, now, quantidade))

            cursor.execute("""
                INSERT INTO movimentacoes (tipo, epi_id, funcionario_id, quantidade,
                                          data_hora, responsavel_entrega, motivo, observacao,
                                          tamanho, estado_conservacao, created_at)
                VALUES ('DEVOLUCAO', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                epi_id,
                funcionario_id,
                quantidade,
                data_hora,
                responsavel.strip(),
                motivo.strip(),
                observacao.strip() if observacao else "",
                tamanho,
                estado_conservacao,
                now
            ))
            last_id = cursor.lastrowid
            conn.commit()

            try:
                from ui.views.tv_mode_view import TVModeWindow
                TVModeWindow.trigger_instant_refresh()
            except Exception:
                pass

            return last_id

    @staticmethod
    def get_movement(movement_id):
        """Retorna os dados detalhados de um lançamento de movimentação."""
        query = """
            SELECT m.id, m.tipo, m.quantidade,
                   CASE 
                       WHEN (m.custo_unitario IS NOT NULL AND m.custo_unitario > 0.0) THEN m.custo_unitario
                       WHEN UPPER(COALESCE(m.estado_conservacao, '')) LIKE '%USADO%' 
                         OR UPPER(COALESCE(m.estado_conservacao, '')) LIKE '%REUTIL%' 
                         OR UPPER(COALESCE(m.estado_conservacao, '')) LIKE '%BOM%' 
                       THEN COALESCE(NULLIF(e.preco_usado, 0.0), e.preco_unitario * 0.5, 0.0)
                       ELSE COALESCE(e.preco_unitario, 0.0)
                   END as custo_unitario,
                   CASE 
                       WHEN (m.custo_total IS NOT NULL AND m.custo_total > 0.0) THEN m.custo_total
                       WHEN (m.custo_unitario IS NOT NULL AND m.custo_unitario > 0.0) THEN m.quantidade * m.custo_unitario
                       WHEN UPPER(COALESCE(m.estado_conservacao, '')) LIKE '%USADO%' 
                         OR UPPER(COALESCE(m.estado_conservacao, '')) LIKE '%REUTIL%' 
                         OR UPPER(COALESCE(m.estado_conservacao, '')) LIKE '%BOM%' 
                       THEN m.quantidade * COALESCE(NULLIF(e.preco_usado, 0.0), e.preco_unitario * 0.5, 0.0)
                       ELSE m.quantidade * COALESCE(e.preco_unitario, 0.0)
                   END as custo_total,
                   m.data_hora, m.responsavel_entrega, m.motivo, m.observacao, m.assinatura_path, m.foto_path,
                   m.tamanho as mov_tamanho, m.estado_conservacao as mov_estado,
                   e.id as epi_id, e.codigo as epi_codigo, e.nome as epi_nome, e.ca as epi_ca, e.unidade as epi_unidade, e.preco_unitario as epi_preco,
                   f.id as func_id, f.matricula as func_matricula, f.nome as func_nome, f.cargo as func_cargo, f.departamento as func_depto
            FROM movimentacoes m
            JOIN epis e ON m.epi_id = e.id
            LEFT JOIN funcionarios f ON m.funcionario_id = f.id
            WHERE m.id = ?
        """
        with get_connection() as conn:
            row = conn.execute(query, (movement_id,)).fetchone()
            return dict(row) if row else None

    @staticmethod
    def delete_movement(movement_id, estornar_estoque=True):
        """
        Exclui um lançamento de movimentação e reverte o estoque correspondente.
        Apenas ADMIN pode executar.
        """
        mov = MovementService.get_movement(movement_id)
        if not mov:
            raise ValueError(f"Lançamento de movimentação ID {movement_id} não encontrado.")

        tipo = mov["tipo"]
        epi_id = mov["epi_id"]
        qtd = mov["quantidade"]
        tam = mov.get("mov_tamanho") or "Único"
        est = (mov.get("mov_estado") or "NOVO").upper()

        with get_connection() as conn:
            cursor = conn.cursor()

            if estornar_estoque:
                if tipo == "SAIDA":
                    cursor.execute("UPDATE epis SET quantidade = quantidade + ? WHERE id = ?", (qtd, epi_id))
                    if "NOVO" in est:
                        cursor.execute("UPDATE epis SET qtd_novos = qtd_novos + ? WHERE id = ?", (qtd, epi_id))
                    else:
                        cursor.execute("UPDATE epis SET qtd_usados_bons = qtd_usados_bons + ? WHERE id = ?", (qtd, epi_id))
                    cursor.execute("""
                        UPDATE epi_grades SET quantidade = quantidade + ?
                        WHERE epi_id = ? AND UPPER(tamanho) = UPPER(?) AND UPPER(estado) = UPPER(?)
                    """, (qtd, epi_id, tam, est))

                elif tipo == "ENTRADA":
                    cursor.execute("UPDATE epis SET quantidade = MAX(0, quantidade - ?) WHERE id = ?", (qtd, epi_id))
                    cursor.execute("UPDATE epis SET qtd_novos = MAX(0, qtd_novos - ?) WHERE id = ?", (qtd, epi_id))
                    cursor.execute("""
                        UPDATE epi_grades SET quantidade = MAX(0, quantidade - ?)
                        WHERE epi_id = ? AND UPPER(tamanho) = UPPER(?) AND UPPER(estado) = UPPER(?)
                    """, (qtd, epi_id, tam, est))

                elif tipo == "DEVOLUCAO":
                    cursor.execute("UPDATE epis SET quantidade = MAX(0, quantidade - ?) WHERE id = ?", (qtd, epi_id))
                    if "NOVO" in est:
                        cursor.execute("UPDATE epis SET qtd_novos = MAX(0, qtd_novos - ?) WHERE id = ?", (qtd, epi_id))
                    else:
                        cursor.execute("UPDATE epis SET qtd_usados_bons = MAX(0, qtd_usados_bons - ?) WHERE id = ?", (qtd, epi_id))
                    cursor.execute("""
                        UPDATE epi_grades SET quantidade = MAX(0, quantidade - ?)
                        WHERE epi_id = ? AND UPPER(tamanho) = UPPER(?);
                    """, (qtd, epi_id, tam))

                elif tipo == "EXTRAVIO_DEMISSAO":
                    # Não altera estoque físico pois o item já estava extraviado
                    pass

            cursor.execute("DELETE FROM movimentacoes WHERE id = ?", (movement_id,))
            conn.commit()

        from services.audit_service import AuditService
        AuditService.log(
            acao="EXCLUSAO_MOVIMENTACAO",
            modulo="MOVIMENTACOES",
            detalhes=f"Lançamento {tipo} ID {movement_id} de {qtd}x '{mov['epi_nome']}' ({tam}, {est}) para '{mov.get('func_nome') or 'N/A'}' foi EXCLUÍDO. Estorno de estoque: {estornar_estoque}."
        )

        try:
            from ui.views.tv_mode_view import TVModeWindow
            TVModeWindow.trigger_instant_refresh()
        except Exception:
            pass

        return True

    @staticmethod
    def update_movement(movement_id, data):
        """
        Atualiza dados de um lançamento de movimentação (apenas ADMIN).
        Suporta alteração de funcionário, EPI, quantidade (com ajuste de estoque), tamanho, estado, data, responsável, motivo e observação.
        """
        mov_antiga = MovementService.get_movement(movement_id)
        if not mov_antiga:
            raise ValueError(f"Lançamento ID {movement_id} não encontrado.")

        tipo = mov_antiga["tipo"]
        epi_antigo_id = mov_antiga["epi_id"]
        qtd_antiga = mov_antiga["quantidade"]
        tam_antigo = mov_antiga.get("mov_tamanho") or "Único"
        est_antigo = (mov_antiga.get("mov_estado") or "NOVO").upper()

        novo_epi_id = int(data.get("epi_id", epi_antigo_id))
        novo_func_id = data.get("funcionario_id")
        if novo_func_id is not None and str(novo_func_id).strip() != "":
            novo_func_id = int(novo_func_id)
        else:
            novo_func_id = None

        nova_qtd = int(data.get("quantidade", qtd_antiga))
        if nova_qtd <= 0:
            raise ValueError("A quantidade deve ser maior que zero!")

        novo_tam = (data.get("tamanho") or "Único").strip()
        novo_est = (data.get("estado_conservacao") or "NOVO").strip().upper()
        novo_resp = (data.get("responsavel_entrega") or mov_antiga["responsavel_entrega"]).strip()
        novo_motivo = (data.get("motivo") or mov_antiga["motivo"]).strip()
        nova_obs = (data.get("observacao") or "").strip()

        dt_raw = data.get("data_hora") or mov_antiga["data_hora"]
        nova_data_hora = MovementService.parse_date(dt_raw)

        with get_connection() as conn:
            cursor = conn.cursor()

            # Busca preço do novo EPI
            cursor.execute("SELECT preco_unitario, nome, quantidade FROM epis WHERE id = ?", (novo_epi_id,))
            epi_row = cursor.fetchone()
            if not epi_row:
                raise ValueError("EPI selecionado não encontrado.")

            if "custo_unitario" in data and data["custo_unitario"] is not None:
                try:
                    custo_unit = float(str(data["custo_unitario"]).replace(",", "."))
                except (ValueError, TypeError):
                    custo_unit = float(epi_row["preco_unitario"] or 0.0)
            else:
                custo_unit = float(mov_antiga.get("custo_unitario") or epi_row["preco_unitario"] or 0.0)
            custo_tot = round(custo_unit * nova_qtd, 2)

            # Ajuste de estoque caso seja SAIDA
            if tipo == "SAIDA":
                if (novo_epi_id != epi_antigo_id) or (novo_tam != tam_antigo) or (novo_est != est_antigo):
                    # Devolve antigo
                    cursor.execute("UPDATE epis SET quantidade = quantidade + ? WHERE id = ?", (qtd_antiga, epi_antigo_id))
                    if "NOVO" in est_antigo:
                        cursor.execute("UPDATE epis SET qtd_novos = qtd_novos + ? WHERE id = ?", (qtd_antiga, epi_antigo_id))
                    else:
                        cursor.execute("UPDATE epis SET qtd_usados_bons = qtd_usados_bons + ? WHERE id = ?", (qtd_antiga, epi_antigo_id))
                    cursor.execute("""
                        UPDATE epi_grades SET quantidade = quantidade + ?
                        WHERE epi_id = ? AND UPPER(tamanho) = UPPER(?) AND UPPER(estado) = UPPER(?)
                    """, (qtd_antiga, epi_antigo_id, tam_antigo, est_antigo))

                    # Desconta novo
                    cursor.execute("UPDATE epis SET quantidade = MAX(0, quantidade - ?) WHERE id = ?", (nova_qtd, novo_epi_id))
                    if "NOVO" in novo_est:
                        cursor.execute("UPDATE epis SET qtd_novos = MAX(0, qtd_novos - ?) WHERE id = ?", (nova_qtd, novo_epi_id))
                    else:
                        cursor.execute("UPDATE epis SET qtd_usados_bons = MAX(0, qtd_usados_bons - ?) WHERE id = ?", (nova_qtd, novo_epi_id))
                    cursor.execute("""
                        UPDATE epi_grades SET quantidade = MAX(0, quantidade - ?)
                        WHERE epi_id = ? AND UPPER(tamanho) = UPPER(?) AND UPPER(estado) = UPPER(?)
                    """, (nova_qtd, novo_epi_id, novo_tam, novo_est))
                else:
                    diff = nova_qtd - qtd_antiga
                    if diff != 0:
                        cursor.execute("UPDATE epis SET quantidade = MAX(0, quantidade - ?) WHERE id = ?", (diff, novo_epi_id))
                        if "NOVO" in novo_est:
                            cursor.execute("UPDATE epis SET qtd_novos = MAX(0, qtd_novos - ?) WHERE id = ?", (diff, novo_epi_id))
                        else:
                            cursor.execute("UPDATE epis SET qtd_usados_bons = MAX(0, qtd_usados_bons - ?) WHERE id = ?", (diff, novo_epi_id))
                        cursor.execute("""
                            UPDATE epi_grades SET quantidade = MAX(0, quantidade - ?)
                            WHERE epi_id = ? AND UPPER(tamanho) = UPPER(?) AND UPPER(estado) = UPPER(?)
                        """, (diff, novo_epi_id, novo_tam, novo_est))

            elif tipo == "ENTRADA":
                diff = nova_qtd - qtd_antiga
                if diff != 0:
                    cursor.execute("UPDATE epis SET quantidade = MAX(0, quantidade + ?) WHERE id = ?", (diff, novo_epi_id))
                    cursor.execute("UPDATE epis SET qtd_novos = MAX(0, qtd_novos + ?) WHERE id = ?", (diff, novo_epi_id))
                    cursor.execute("""
                        UPDATE epi_grades SET quantidade = MAX(0, quantidade + ?)
                        WHERE epi_id = ? AND UPPER(tamanho) = UPPER(?) AND UPPER(estado) = UPPER(?)
                    """, (diff, novo_epi_id, novo_tam, novo_est))

            # Atualiza o registro na tabela movimentacoes
            cursor.execute("""
                UPDATE movimentacoes
                SET epi_id = ?, funcionario_id = ?, quantidade = ?,
                    custo_unitario = ?, custo_total = ?, data_hora = ?,
                    responsavel_entrega = ?, motivo = ?, observacao = ?,
                    tamanho = ?, estado_conservacao = ?
                WHERE id = ?
            """, (
                novo_epi_id, novo_func_id, nova_qtd,
                custo_unit, custo_tot, nova_data_hora,
                novo_resp, novo_motivo, nova_obs,
                novo_tam, novo_est,
                movement_id
            ))
            conn.commit()

        from services.audit_service import AuditService
        AuditService.log(
            acao="EDICAO_MOVIMENTACAO",
            modulo="MOVIMENTACOES",
            detalhes=f"Lançamento {tipo} ID {movement_id} alterado pelo Admin. Qtd: {qtd_antiga}->{nova_qtd}, EPI ID: {epi_antigo_id}->{novo_epi_id}, Data: {nova_data_hora}."
        )

        try:
            from ui.views.tv_mode_view import TVModeWindow
            TVModeWindow.trigger_instant_refresh()
        except Exception:
            pass

        return True

    @staticmethod
    def list_movements(tipo=None, epi_id=None, funcionario_id=None,
                       data_inicio=None, data_fim=None, search=None, limit=200):
        query = """
            SELECT m.id, m.tipo, m.quantidade,
                   CASE 
                       WHEN (m.custo_unitario IS NOT NULL AND m.custo_unitario > 0.0) THEN m.custo_unitario
                       WHEN UPPER(COALESCE(m.estado_conservacao, '')) LIKE '%USADO%' 
                         OR UPPER(COALESCE(m.estado_conservacao, '')) LIKE '%REUTIL%' 
                         OR UPPER(COALESCE(m.estado_conservacao, '')) LIKE '%BOM%' 
                       THEN COALESCE(NULLIF(e.preco_usado, 0.0), e.preco_unitario * 0.5, 0.0)
                       ELSE COALESCE(e.preco_unitario, 0.0)
                   END as custo_unitario,
                   CASE 
                       WHEN (m.custo_total IS NOT NULL AND m.custo_total > 0.0) THEN m.custo_total
                       WHEN (m.custo_unitario IS NOT NULL AND m.custo_unitario > 0.0) THEN m.quantidade * m.custo_unitario
                       WHEN UPPER(COALESCE(m.estado_conservacao, '')) LIKE '%USADO%' 
                         OR UPPER(COALESCE(m.estado_conservacao, '')) LIKE '%REUTIL%' 
                         OR UPPER(COALESCE(m.estado_conservacao, '')) LIKE '%BOM%' 
                       THEN m.quantidade * COALESCE(NULLIF(e.preco_usado, 0.0), e.preco_unitario * 0.5, 0.0)
                       ELSE m.quantidade * COALESCE(e.preco_unitario, 0.0)
                   END as custo_total,
                   m.data_hora, m.responsavel_entrega, m.motivo, m.observacao, m.assinatura_path, m.foto_path,
                   m.tamanho as mov_tamanho, m.estado_conservacao as mov_estado,
                   e.id as epi_id, e.codigo as epi_codigo, e.nome as epi_nome, e.ca as epi_ca, e.unidade as epi_unidade,
                   f.id as func_id, f.matricula as func_matricula, f.nome as func_nome, f.cargo as func_cargo, f.departamento as func_depto
            FROM movimentacoes m
            JOIN epis e ON m.epi_id = e.id
            LEFT JOIN funcionarios f ON m.funcionario_id = f.id
            WHERE 1=1
        """
        params = []

        if tipo and tipo != "TODOS":
            t_upper = tipo.upper()
            if "NÃO DEVOLVIDO" in t_upper or "NAO DEVOLVIDO" in t_upper or "EXTRAVIO" in t_upper:
                query += " AND (m.tipo = 'EXTRAVIO_DEMISSAO' OR m.tipo = 'NÃO DEVOLVIDO' OR UPPER(m.estado_conservacao) LIKE '%NÃO DEVOLV%' OR UPPER(m.estado_conservacao) LIKE '%NAO DEVOLV%' OR UPPER(m.estado_conservacao) LIKE '%RETIDO%')"
            elif t_upper == "DEVOLUCAO":
                query += " AND m.tipo = 'DEVOLUCAO' AND UPPER(COALESCE(m.estado_conservacao, '')) NOT LIKE '%NÃO DEVOLV%' AND UPPER(COALESCE(m.estado_conservacao, '')) NOT LIKE '%NAO DEVOLV%' AND UPPER(COALESCE(m.estado_conservacao, '')) NOT LIKE '%RETIDO%'"
            else:
                query += " AND m.tipo = ?"
                params.append(tipo)

        if epi_id:
            query += " AND m.epi_id = ?"
            params.append(epi_id)

        if funcionario_id:
            query += " AND m.funcionario_id = ?"
            params.append(funcionario_id)

        if data_inicio:
            dt_ini_norm = MovementService.normalize_date_iso(data_inicio)
            if dt_ini_norm:
                query += " AND date(m.data_hora) >= date(?)"
                params.append(dt_ini_norm)

        if data_fim:
            dt_fim_norm = MovementService.normalize_date_iso(data_fim)
            if dt_fim_norm:
                query += " AND date(m.data_hora) <= date(?)"
                params.append(dt_fim_norm)

        if search:
            query += """ AND (
                e.nome LIKE ? OR e.codigo LIKE ? OR e.ca LIKE ? OR
                f.nome LIKE ? OR f.matricula LIKE ? OR
                m.responsavel_entrega LIKE ? OR m.motivo LIKE ? OR
                m.observacao LIKE ? OR
                m.data_hora LIKE ? OR
                strftime('%d/%m/%Y', m.data_hora) LIKE ? OR
                strftime('%d/%m', m.data_hora) LIKE ?
            )"""
            s = f"%{search.strip()}%"
            norm_search = MovementService.normalize_date_iso(search.strip())
            s_iso = f"%{norm_search}%" if norm_search else s
            params.extend([s, s, s, s, s, s, s, s, s_iso, s, s])

        query += " ORDER BY m.data_hora DESC"

        if limit:
            query += f" LIMIT {int(limit)}"

        with get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def get_operators():
        with get_connection() as conn:
            rows = conn.execute("SELECT nome FROM operadores WHERE ativo = 1 ORDER BY nome ASC").fetchall()
            return [r["nome"] for r in rows]

    @staticmethod
    def list_pending_replacements():
        """
        Retorna lista de entregas onde a vida útil do EPI já expirou
        e o funcionário ainda não recebeu uma nova troca.
        """
        query = """
            SELECT m.id as mov_id, m.data_hora, m.quantidade,
                   e.id as epi_id, e.codigo as epi_codigo, e.nome as epi_nome, e.ca as epi_ca, e.dias_vida_util,
                   f.id as func_id, f.matricula as func_matricula, f.nome as func_nome, f.cargo as func_cargo, f.departamento as func_depto
            FROM movimentacoes m
            JOIN epis e ON m.epi_id = e.id
            JOIN funcionarios f ON m.funcionario_id = f.id
            WHERE m.tipo = 'SAIDA' AND e.dias_vida_util > 0 AND f.status = 'Ativo'
            ORDER BY m.data_hora DESC
        """
        with get_connection() as conn:
            rows = conn.execute(query).fetchall()

        now = datetime.now()
        vencidos = []
        for r in rows:
            try:
                dt_entrega = datetime.strptime(r["data_hora"][:19], "%Y-%m-%d %H:%M:%S")
                dias_passados = (now - dt_entrega).days
                vida_util = r["dias_vida_util"]

                if dias_passados >= vida_util:
                    item = dict(r)
                    item["dias_em_uso"] = dias_passados
                    item["dias_vencido"] = dias_passados - vida_util
                    item["data_prevista_troca"] = (dt_entrega + timedelta(days=vida_util)).strftime("%d/%m/%Y")
                    vencidos.append(item)
            except Exception:
                pass

        return vencidos

    @staticmethod
    def get_financial_summary(mes_ano=None):
        """Retorna custos totais de saídas por setor no mês."""
        if not mes_ano:
            mes_ano = datetime.now().strftime("%Y-%m")

        with get_connection() as conn:
            custo_total_mes = conn.execute("""
                SELECT COALESCE(SUM(
                    CASE 
                        WHEN (m.custo_total IS NOT NULL AND m.custo_total > 0.0) THEN m.custo_total
                        WHEN (m.custo_unitario IS NOT NULL AND m.custo_unitario > 0.0) THEN m.quantidade * m.custo_unitario
                        WHEN UPPER(COALESCE(m.estado_conservacao, '')) LIKE '%USADO%' 
                          OR UPPER(COALESCE(m.estado_conservacao, '')) LIKE '%REUTIL%' 
                          OR UPPER(COALESCE(m.estado_conservacao, '')) LIKE '%BOM%' 
                        THEN m.quantidade * COALESCE(NULLIF(e.preco_usado, 0.0), e.preco_unitario * 0.5, 0.0)
                        ELSE m.quantidade * COALESCE(e.preco_unitario, 0.0)
                    END
                ), 0.0)
                FROM movimentacoes m
                JOIN epis e ON m.epi_id = e.id
                WHERE m.tipo = 'SAIDA' AND strftime('%Y-%m', m.data_hora) = ?
            """, (mes_ano,)).fetchone()[0]

            por_setor = conn.execute("""
                SELECT f.departamento, 
                       COALESCE(SUM(
                           CASE 
                               WHEN (m.custo_total IS NOT NULL AND m.custo_total > 0.0) THEN m.custo_total
                               WHEN (m.custo_unitario IS NOT NULL AND m.custo_unitario > 0.0) THEN m.quantidade * m.custo_unitario
                               WHEN UPPER(COALESCE(m.estado_conservacao, '')) LIKE '%USADO%' 
                                 OR UPPER(COALESCE(m.estado_conservacao, '')) LIKE '%REUTIL%' 
                                 OR UPPER(COALESCE(m.estado_conservacao, '')) LIKE '%BOM%' 
                               THEN m.quantidade * COALESCE(NULLIF(e.preco_usado, 0.0), e.preco_unitario * 0.5, 0.0)
                               ELSE m.quantidade * COALESCE(e.preco_unitario, 0.0)
                           END
                       ), 0.0) as total_gasto, 
                       COUNT(m.id) as total_entregas
                FROM movimentacoes m
                JOIN epis e ON m.epi_id = e.id
                JOIN funcionarios f ON m.funcionario_id = f.id
                WHERE m.tipo = 'SAIDA' AND strftime('%Y-%m', m.data_hora) = ?
                GROUP BY f.departamento
                ORDER BY total_gasto DESC
            """, (mes_ano,)).fetchall()

            return {
                "custo_total_mes": custo_total_mes,
                "por_setor": [dict(r) for r in por_setor]
            }

    @staticmethod
    def get_recent_stats():
        with get_connection() as conn:
            hoje = datetime.now().strftime("%Y-%m-%d")
            mes_atual = datetime.now().strftime("%Y-%m")

            saidas_hoje = conn.execute("""
                SELECT COALESCE(SUM(quantidade), 0)
                FROM movimentacoes
                WHERE tipo = 'SAIDA' AND date(data_hora) = date(?)
            """, (hoje,)).fetchone()[0]

            saidas_mes = conn.execute("""
                SELECT COALESCE(SUM(quantidade), 0)
                FROM movimentacoes
                WHERE tipo = 'SAIDA' AND strftime('%Y-%m', data_hora) = ?
            """, (mes_atual,)).fetchone()[0]

            custo_saidas_mes = conn.execute("""
                SELECT COALESCE(SUM(
                    CASE 
                        WHEN (m.custo_total IS NOT NULL AND m.custo_total > 0.0) THEN m.custo_total
                        WHEN (m.custo_unitario IS NOT NULL AND m.custo_unitario > 0.0) THEN m.quantidade * m.custo_unitario
                        WHEN UPPER(COALESCE(m.estado_conservacao, '')) LIKE '%USADO%' 
                          OR UPPER(COALESCE(m.estado_conservacao, '')) LIKE '%REUTIL%' 
                          OR UPPER(COALESCE(m.estado_conservacao, '')) LIKE '%BOM%' 
                        THEN m.quantidade * COALESCE(NULLIF(e.preco_usado, 0.0), e.preco_unitario * 0.5, 0.0)
                        ELSE m.quantidade * COALESCE(e.preco_unitario, 0.0)
                    END
                ), 0.0)
                FROM movimentacoes m
                JOIN epis e ON m.epi_id = e.id
                WHERE m.tipo = 'SAIDA' AND strftime('%Y-%m', m.data_hora) = ?
            """, (mes_atual,)).fetchone()[0]

            ultimas_saidas = conn.execute("""
                SELECT m.id, m.tipo, m.quantidade, 
                       CASE 
                           WHEN (m.custo_total IS NOT NULL AND m.custo_total > 0.0) THEN m.custo_total
                           WHEN (m.custo_unitario IS NOT NULL AND m.custo_unitario > 0.0) THEN m.quantidade * m.custo_unitario
                           WHEN UPPER(COALESCE(m.estado_conservacao, '')) LIKE '%USADO%' 
                             OR UPPER(COALESCE(m.estado_conservacao, '')) LIKE '%REUTIL%' 
                             OR UPPER(COALESCE(m.estado_conservacao, '')) LIKE '%BOM%' 
                           THEN m.quantidade * COALESCE(NULLIF(e.preco_usado, 0.0), e.preco_unitario * 0.5, 0.0)
                           ELSE m.quantidade * COALESCE(e.preco_unitario, 0.0)
                       END as custo_total,
                       m.data_hora, m.responsavel_entrega,
                       e.nome as epi_nome, e.ca as epi_ca,
                       f.nome as func_nome
                FROM movimentacoes m
                JOIN epis e ON m.epi_id = e.id
                LEFT JOIN funcionarios f ON m.funcionario_id = f.id
                ORDER BY m.data_hora DESC
                LIMIT 8
            """).fetchall()

            return {
                "saidas_hoje": saidas_hoje,
                "saidas_mes": saidas_mes,
                "custo_saidas_mes": custo_saidas_mes,
                "ultimas_saidas": [dict(r) for r in ultimas_saidas]
            }
