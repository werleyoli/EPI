from database import get_connection
from datetime import datetime, timedelta

class EPIService:
    @staticmethod
    def list_epis(search="", filter_status="all", show_inactive=False, filter_grupo="all"):
        """
        Retorna lista de EPIs com filtros opcionais.
        filter_status: 'all', 'low' (estoque baixo), 'ok', 'out' (zerado), 'ca_expiring' (CA vencendo)
        filter_grupo: 'all' ou nome de um grupo específico
        """
        query = """
            SELECT id, codigo, nome, ca, validade_ca, fabricante, tamanho,
                   unidade, quantidade, estoque_minimo, preco_unitario,
                   COALESCE(preco_usado, ROUND(preco_unitario * 0.5, 2), 0.0) as preco_usado,
                   dias_vida_util,
                   localizacao, localizacao_secundaria, descricao, ativo, grupo, qtd_novos, qtd_usados_bons,
                   qtd_ruins, qtd_descarte, grade_resumo
            FROM epis
            WHERE 1=1
        """
        params = []

        if not show_inactive:
            query += " AND ativo = 1"

        if filter_grupo and filter_grupo != "all" and filter_grupo != "TODOS OS GRUPOS":
            query += " AND UPPER(grupo) = UPPER(?)"
            params.append(filter_grupo.strip())

        if search:
            query += " AND (codigo LIKE ? OR nome LIKE ? OR ca LIKE ? OR fabricante LIKE ? OR grupo LIKE ?)"
            s = f"%{search.strip()}%"
            params.extend([s, s, s, s, s])

        query += " ORDER BY grupo ASC, nome ASC"

        with get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            epis = [dict(r) for r in rows]

        now_date = datetime.now().date()

        if filter_status == "low":
            epis = [e for e in epis if 0 < e["quantidade"] <= e["estoque_minimo"]]
        elif filter_status == "out":
            epis = [e for e in epis if e["quantidade"] == 0]
        elif filter_status == "ok":
            epis = [e for e in epis if e["quantidade"] > e["estoque_minimo"]]
        elif filter_status == "quarentena":
            # Itens com saldo em manutenção (qtd_ruins) ou descarte (qtd_descarte)
            epis = [e for e in epis if (e.get("qtd_ruins", 0) or 0) > 0 or (e.get("qtd_descarte", 0) or 0) > 0]
        elif filter_status == "ca_expiring":
            # C.A. vencido ou vencendo em 60 dias
            result = []
            for e in epis:
                if e.get("validade_ca"):
                    try:
                        val_dt = datetime.strptime(e["validade_ca"][:10], "%Y-%m-%d").date()
                        dias = (val_dt - now_date).days
                        if dias <= 60:
                            e["dias_restantes_ca"] = dias
                            result.append(e)
                    except Exception:
                        pass
            return result

        return epis

    @staticmethod
    def get_epi(epi_id):
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM epis WHERE id = ?", (epi_id,)).fetchone()
            return dict(row) if row else None

    @staticmethod
    def create_epi(data):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with get_connection() as conn:
            cursor = conn.cursor()
            preco = float(data.get("preco_unitario", 0.0) or 0.0)
            preco_usado = float(data.get("preco_usado", 0.0) or 0.0)
            if preco_usado <= 0.0 and preco > 0.0:
                preco_usado = round(preco * 0.5, 2)
            vida_util = int(data.get("dias_vida_util", 0) or 0)
            grupo = (data.get("grupo") or "DIVERSOS / OUTROS").strip().upper()

            # Garante que o grupo existe na tabela de grupos
            cursor.execute("INSERT OR IGNORE INTO grupos_epi (nome, descricao, created_at) VALUES (?, ?, ?);",
                           (grupo, f"Grupo {grupo}", now))

            cursor.execute("""
                INSERT INTO epis (codigo, nome, ca, validade_ca, fabricante, tamanho,
                                  unidade, quantidade, estoque_minimo, preco_unitario, preco_usado, dias_vida_util,
                                  localizacao, localizacao_secundaria, descricao, ativo, grupo, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            """, (
                data["codigo"].strip().upper(),
                data["nome"].strip(),
                data["ca"].strip(),
                data.get("validade_ca", "").strip() or None,
                data.get("fabricante", "").strip(),
                data.get("tamanho", "").strip(),
                data.get("unidade", "UN").strip().upper(),
                int(data.get("quantidade", 0)),
                int(data.get("estoque_minimo", 5)),
                preco,
                preco_usado,
                vida_util,
                data.get("localizacao", "").strip(),
                data.get("localizacao_secundaria", "").strip(),
                data.get("descricao", "").strip(),
                grupo,
                now
            ))
            epi_id = cursor.lastrowid

            # Se não houver grades customizadas, cria grade padrão
            if not ("grades" in data and data["grades"]):
                tam = data.get("tamanho", "Único").strip() or "Único"
                qtd_ini = int(data.get("quantidade", 0))
                cursor.execute("""
                    INSERT OR IGNORE INTO epi_grades (epi_id, tamanho, estado, quantidade, created_at)
                    VALUES (?, ?, 'NOVO', ?, ?);
                """, (epi_id, tam, qtd_ini, now))
                cursor.execute("UPDATE epis SET qtd_novos = ? WHERE id = ?;", (qtd_ini, epi_id))

            qtd_inicial = int(data.get("quantidade", 0))
            if qtd_inicial > 0:
                resp = data.get("responsavel", "Sistema")
                custo_tot = qtd_inicial * preco
                cursor.execute("""
                    INSERT INTO movimentacoes (tipo, epi_id, funcionario_id, quantidade, custo_unitario, custo_total,
                                              data_hora, responsavel_entrega, motivo, observacao, created_at)
                    VALUES ('ENTRADA', ?, NULL, ?, ?, ?, ?, ?, 'Saldo Inicial de Cadastro', 'Cadastro inicial do EPI', ?)
                """, (epi_id, qtd_inicial, preco, custo_tot, now, resp, now))

            conn.commit()

        # Salva grade de variações após fechar a primeira transação
        if "grades" in data and data["grades"]:
            EPIService.save_epi_grades(epi_id, data["grades"])
            with get_connection() as conn:
                epi = conn.execute("SELECT quantidade, preco_unitario FROM epis WHERE id = ?", (epi_id,)).fetchone()
                if epi and epi["quantidade"] > 0:
                    q_real = epi["quantidade"]
                    c_tot = q_real * (epi["preco_unitario"] or 0.0)
                    conn.execute("""
                        UPDATE movimentacoes
                        SET quantidade = ?, custo_total = ?
                        WHERE epi_id = ? AND motivo = 'Saldo Inicial de Cadastro';
                    """, (q_real, c_tot, epi_id))
                    conn.commit()

        try:
            from ui.views.tv_mode_view import TVModeWindow
            TVModeWindow.trigger_instant_refresh()
        except Exception:
            pass

        return epi_id

    @staticmethod
    def update_epi(epi_id, data):
        preco = float(data.get("preco_unitario", 0.0) or 0.0)
        preco_usado = float(data.get("preco_usado", 0.0) or 0.0)
        if preco_usado <= 0.0 and preco > 0.0:
            preco_usado = round(preco * 0.5, 2)
        vida_util = int(data.get("dias_vida_util", 0) or 0)
        grupo = (data.get("grupo") or "DIVERSOS / OUTROS").strip().upper()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with get_connection() as conn:
            # Garante que o grupo existe
            conn.execute("INSERT OR IGNORE INTO grupos_epi (nome, descricao, created_at) VALUES (?, ?, ?);",
                         (grupo, f"Grupo {grupo}", now))

            conn.execute("""
                UPDATE epis
                SET codigo = ?, nome = ?, ca = ?, validade_ca = ?, fabricante = ?,
                    tamanho = ?, unidade = ?, estoque_minimo = ?, preco_unitario = ?, preco_usado = ?,
                    dias_vida_util = ?, localizacao = ?, localizacao_secundaria = ?, descricao = ?, grupo = ?
                WHERE id = ?
            """, (
                data["codigo"].strip().upper(),
                data["nome"].strip(),
                data["ca"].strip(),
                data.get("validade_ca", "").strip() or None,
                data.get("fabricante", "").strip(),
                data.get("tamanho", "").strip(),
                data.get("unidade", "UN").strip().upper(),
                int(data.get("estoque_minimo", 5)),
                preco,
                preco_usado,
                vida_util,
                data.get("localizacao", "").strip(),
                data.get("localizacao_secundaria", "").strip(),
                data.get("descricao", "").strip(),
                grupo,
                epi_id
            ))
            conn.commit()

        # Atualiza a grade se fornecida
        if "grades" in data and data["grades"]:
            EPIService.save_epi_grades(epi_id, data["grades"])

        try:
            from ui.views.tv_mode_view import TVModeWindow
            TVModeWindow.trigger_instant_refresh()
        except Exception:
            pass

        return True

    @staticmethod
    def get_epi_grades(epi_id):
        """Retorna lista de variações de tamanho e estados de conservação para o EPI."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, tamanho, estado, quantidade
                FROM epi_grades
                WHERE epi_id = ?
                ORDER BY id ASC;
            """, (epi_id,))
            rows = cursor.fetchall()

            grouped = {}
            for r in rows:
                tam = str(r["tamanho"]).strip()
                if tam not in grouped:
                    grouped[tam] = {"tamanho": tam, "novo": 0, "usado_bom": 0, "ruim": 0, "descarte": 0}
                est = (r["estado"] or "").upper()
                qtd = int(r["quantidade"] or 0)
                if "NOVO" in est:
                    grouped[tam]["novo"] += qtd
                elif "BOM" in est or "REUTIL" in est or "HIGIEN" in est:
                    grouped[tam]["usado_bom"] += qtd
                elif "RUIM" in est or "MANUT" in est or "REPAR" in est:
                    grouped[tam]["ruim"] += qtd
                elif "DESC" in est or "SUCATA" in est or "INSERV" in est:
                    grouped[tam]["descarte"] += qtd
                else:
                    grouped[tam]["novo"] += qtd

            for tam, d in grouped.items():
                d["total_disponivel"] = d["novo"] + d["usado_bom"]

            return list(grouped.values())

    @staticmethod
    def get_epi_stock_items(epi_id):
        """
        Retorna as variações físicas do EPI detalhadas por tamanho e estado de conservação.
        Cada item retornado contém:
        {"tamanho": ..., "estado": ..., "quantidade": ...}
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT tamanho, estado, quantidade
                FROM epi_grades
                WHERE epi_id = ?
                ORDER BY id ASC;
            """, (epi_id,))
            rows = cursor.fetchall()
            if rows:
                return [dict(r) for r in rows]

            # Fallback se não houver registros em epi_grades
            epi = conn.execute("SELECT tamanho, quantidade, qtd_novos, qtd_usados_bons FROM epis WHERE id = ?;", (epi_id,)).fetchone()
            if not epi:
                return []

            tam = epi["tamanho"] or "Único"
            novos = epi["qtd_novos"] or epi["quantidade"] or 0
            usados = epi["qtd_usados_bons"] or 0
            items = []
            if novos > 0:
                items.append({"tamanho": tam, "estado": "NOVO", "quantidade": novos})
            if usados > 0:
                items.append({"tamanho": tam, "estado": "BOM", "quantidade": usados})
            if not items:
                items.append({"tamanho": tam, "estado": "NOVO", "quantidade": epi["quantidade"] or 0})
            return items

    @staticmethod
    def save_epi_grades(epi_id, grades_data):
        """
        Salva as variações de tamanho e quantidades por estado de conservação.
        grades_data: list de dicts com {"tamanho", "novo", "usado_bom", "ruim", "descarte"}
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM epi_grades WHERE epi_id = ?;", (epi_id,))

            tot_novos = 0
            tot_usados = 0
            tot_ruins = 0
            tot_descarte = 0
            tamanhos_ativos = []

            # Agrupa por tamanho para consolidar caso o usuário tenha inserido linhas repetidas
            merged_grades = {}
            for g in grades_data:
                tam = str(g.get("tamanho", "")).strip() or "Único"
                if tam not in merged_grades:
                    merged_grades[tam] = {"novo": 0, "usado_bom": 0, "ruim": 0, "descarte": 0}
                merged_grades[tam]["novo"] += max(0, int(g.get("novo", 0) or 0))
                merged_grades[tam]["usado_bom"] += max(0, int(g.get("usado_bom", 0) or 0))
                merged_grades[tam]["ruim"] += max(0, int(g.get("ruim", 0) or 0))
                merged_grades[tam]["descarte"] += max(0, int(g.get("descarte", 0) or 0))

            for tam, m_data in merged_grades.items():
                q_novo = m_data["novo"]
                q_usado = m_data["usado_bom"]
                q_ruim = m_data["ruim"]
                q_desc = m_data["descarte"]

                tot_novos += q_novo
                tot_usados += q_usado
                tot_ruins += q_ruim
                tot_descarte += q_desc

                tot_tam = q_novo + q_usado
                if tot_tam > 0 or (q_ruim + q_desc) > 0:
                    tamanhos_ativos.append(f"{tam} ({tot_tam} un)" if tot_tam > 0 else f"{tam} (0)")

                if q_novo > 0:
                    cursor.execute("INSERT OR REPLACE INTO epi_grades (epi_id, tamanho, estado, quantidade, created_at) VALUES (?, ?, 'NOVO', ?, ?);",
                                   (epi_id, tam, q_novo, now))
                if q_usado > 0:
                    cursor.execute("INSERT OR REPLACE INTO epi_grades (epi_id, tamanho, estado, quantidade, created_at) VALUES (?, ?, 'BOM / REUTILIZÁVEL', ?, ?);",
                                   (epi_id, tam, q_usado, now))
                if q_ruim > 0:
                    cursor.execute("INSERT OR REPLACE INTO epi_grades (epi_id, tamanho, estado, quantidade, created_at) VALUES (?, ?, 'RUIM / REPARO', ?, ?);",
                                   (epi_id, tam, q_ruim, now))
                if q_desc > 0:
                    cursor.execute("INSERT OR REPLACE INTO epi_grades (epi_id, tamanho, estado, quantidade, created_at) VALUES (?, ?, 'DESCARTE / SUCATA', ?, ?);",
                                   (epi_id, tam, q_desc, now))

            tot_disponivel = tot_novos + tot_usados
            grade_resumo = ", ".join(tamanhos_ativos)
            tamanho_display = ", ".join([str(g.get("tamanho", "")).strip() for g in grades_data if str(g.get("tamanho", "")).strip()]) or "Único"

            cursor.execute("""
                UPDATE epis
                SET quantidade = ?,
                    qtd_novos = ?,
                    qtd_usados_bons = ?,
                    qtd_ruins = ?,
                    qtd_descarte = ?,
                    tamanho = ?,
                    grade_resumo = ?
                WHERE id = ?;
            """, (tot_disponivel, tot_novos, tot_usados, tot_ruins, tot_descarte, tamanho_display, grade_resumo, epi_id))

            conn.commit()

        try:
            from ui.views.tv_mode_view import TVModeWindow
            TVModeWindow.trigger_instant_refresh()
        except Exception:
            pass

        return True

    @staticmethod
    def get_available_sizes(epi_id):
        """Retorna tamanhos disponíveis para entrega e saldos."""
        grades = EPIService.get_epi_grades(epi_id)
        if not grades:
            epi = EPIService.get_epi(epi_id)
            if epi:
                raw_tam = str(epi.get("tamanho") or "Único").strip()
                if "," in raw_tam:
                    t_list = [x.strip() for x in raw_tam.split(",") if x.strip()]
                    return [{
                        "tamanho": t,
                        "novo": epi.get("qtd_novos", epi.get("quantidade", 0)),
                        "usado_bom": epi.get("qtd_usados_bons", 0),
                        "total_disponivel": epi.get("quantidade", 0)
                    } for t in t_list]
                return [{
                    "tamanho": raw_tam or "Único",
                    "novo": epi.get("qtd_novos", epi.get("quantidade", 0)),
                    "usado_bom": epi.get("qtd_usados_bons", 0),
                    "total_disponivel": epi.get("quantidade", 0)
                }]
            return []

        expanded = []
        for g in grades:
            t = str(g.get("tamanho", "")).strip()
            if "," in t:
                for sub in t.split(","):
                    if sub.strip():
                        copy_g = dict(g)
                        copy_g["tamanho"] = sub.strip()
                        expanded.append(copy_g)
            else:
                expanded.append(g)
        return expanded

    @staticmethod
    def list_grupos():
        """Retorna lista de grupos cadastrados com estatísticas de SKUs e saldo."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT g.id, g.nome, g.descricao,
                       (SELECT COUNT(*) FROM epis e WHERE e.ativo = 1 AND UPPER(e.grupo) = UPPER(g.nome)) as total_itens,
                       (SELECT COALESCE(SUM(e.quantidade), 0) FROM epis e WHERE e.ativo = 1 AND UPPER(e.grupo) = UPPER(g.nome)) as total_saldo
                FROM grupos_epi g
                ORDER BY g.nome ASC;
            """)
            return [dict(r) for r in cursor.fetchall()]

    @staticmethod
    def list_nomes_grupos():
        """Retorna apenas os nomes ordenados para ComboBox."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT nome FROM grupos_epi ORDER BY nome ASC;")
            rows = cursor.fetchall()
            return [r[0] for r in rows] if rows else [
                "BOTA DE PVC", "BOTA TÉRMICA", "CALÇADOS & BOTINAS DE SEGURANÇA",
                "CAMISAS DE SEGURANÇA / UNIFORMES", "VESTIMENTAS & UNIFORMES",
                "LUVAS DE PROTEÇÃO", "LUVAS DE VAQUETA / RASPA", "LUVAS NITRÍLICAS / BORRACHA",
                "ÓCULOS & PROTEÇÃO FACIAL", "CAPACETES DE SEGURANÇA", "PROTEÇÃO AUDITIVA",
                "PROTEÇÃO RESPIRATÓRIA", "TRABALHO EM ALTURA", "DIVERSOS / OUTROS"
            ]

    @staticmethod
    def create_grupo(nome, descricao=""):
        nome = (nome or "").strip().upper()
        if not nome:
            raise ValueError("O nome do grupo não pode ser vazio.")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with get_connection() as conn:
            conn.execute("INSERT OR IGNORE INTO grupos_epi (nome, descricao, created_at) VALUES (?, ?, ?);",
                         (nome, descricao or f"Grupo {nome}", now))
            conn.commit()
        return True

    @staticmethod
    def delete_grupo(nome):
        nome = (nome or "").strip().upper()
        if nome in ["DIVERSOS / OUTROS", "GERAL"]:
            raise ValueError("O grupo padrão 'DIVERSOS / OUTROS' não pode ser excluído.")
        with get_connection() as conn:
            conn.execute("UPDATE epis SET grupo = 'DIVERSOS / OUTROS' WHERE UPPER(grupo) = UPPER(?);", (nome,))
            conn.execute("DELETE FROM grupos_epi WHERE UPPER(nome) = UPPER(?);", (nome,))
            conn.commit()
        return True

    @staticmethod
    def reassign_epi_grupo(epi_id, novo_grupo):
        novo_grupo = (novo_grupo or "DIVERSOS / OUTROS").strip().upper()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with get_connection() as conn:
            conn.execute("INSERT OR IGNORE INTO grupos_epi (nome, descricao, created_at) VALUES (?, ?, ?);",
                         (novo_grupo, f"Grupo {novo_grupo}", now))
            conn.execute("UPDATE epis SET grupo = ? WHERE id = ?;", (novo_grupo, epi_id))
            conn.commit()
        return True

    @staticmethod
    def get_summary():
        """Retorna indicadores do estoque, incluindo custos e alertas de CA."""
        with get_connection() as conn:
            total_itens = conn.execute("SELECT COUNT(*) FROM epis WHERE ativo = 1").fetchone()[0]
            total_unidades = conn.execute("SELECT COALESCE(SUM(quantidade), 0) FROM epis WHERE ativo = 1").fetchone()[0]
            valor_total_estoque = conn.execute("SELECT COALESCE(SUM(quantidade * preco_unitario), 0.0) FROM epis WHERE ativo = 1").fetchone()[0]
            criticos = conn.execute("SELECT COUNT(*) FROM epis WHERE ativo = 1 AND quantidade <= estoque_minimo").fetchone()[0]
            zerados = conn.execute("SELECT COUNT(*) FROM epis WHERE ativo = 1 AND quantidade = 0").fetchone()[0]

            # Validade do CA
            hoje = datetime.now().strftime("%Y-%m-%d")
            data_limite_60d = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")

            ca_vencidos = conn.execute("SELECT COUNT(*) FROM epis WHERE ativo = 1 AND validade_ca IS NOT NULL AND validade_ca < ?", (hoje,)).fetchone()[0]
            ca_vencendo = conn.execute("SELECT COUNT(*) FROM epis WHERE ativo = 1 AND validade_ca IS NOT NULL AND validade_ca >= ? AND validade_ca <= ?", (hoje, data_limite_60d)).fetchone()[0]

            return {
                "total_itens": total_itens,
                "total_unidades": total_unidades,
                "valor_total_estoque": valor_total_estoque,
                "criticos": criticos,
                "zerados": zerados,
                "ca_vencidos": ca_vencidos,
                "ca_vencendo": ca_vencendo
            }
