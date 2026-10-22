from database import get_connection
from datetime import datetime

class EmployeeService:
    @staticmethod
    def list_employees(search="", status="all", show_inactive=False):
        """Retorna lista de funcionários com filtros inteligentes de status."""
        query = """
            SELECT id, matricula, nome, cpf, cargo, departamento,
                   data_admissao, status, observacoes, telefone,
                   tamanho_calcado, tamanho_luva, tamanho_uniforme, tamanho_mascara
            FROM funcionarios
            WHERE 1=1
        """
        params = []

        if not show_inactive:
            if status and status != "all" and status != "Todos":
                if status == "Ativo":
                    query += " AND status = 'Ativo'"
                elif status in ("Inativo", "Desligado", "inativo", "desligado"):
                    query += " AND status != 'Ativo'"
                elif "Pendência" in status or "pendente" in status.lower():
                    query += " AND status LIKE '%Pendência%'"
                elif status == "Afastado":
                    query += " AND status = 'Afastado'"
                else:
                    query += " AND status = ?"
                    params.append(status)

        if search:
            query += " AND (matricula LIKE ? OR nome LIKE ? OR cpf LIKE ? OR cargo LIKE ? OR departamento LIKE ?)"
            s = f"%{search.strip()}%"
            params.extend([s, s, s, s, s])

        query += " ORDER BY status ASC, nome ASC"

        with get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def get_employee(func_id):
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM funcionarios WHERE id = ?", (func_id,)).fetchone()
            return dict(row) if row else None

    @staticmethod
    def create_employee(data):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        depto = (data.get("departamento") or "Geral").strip()
        with get_connection() as conn:
            cursor = conn.cursor()
            # Garante que o departamento existe na tabela departamentos
            cursor.execute("INSERT OR IGNORE INTO departamentos (nome, descricao, created_at) VALUES (?, ?, ?);",
                           (depto, f"Setor {depto}", now))

            cursor.execute("""
                INSERT INTO funcionarios (matricula, nome, cpf, cargo, departamento,
                                         data_admissao, status, observacoes, telefone,
                                         tamanho_calcado, tamanho_luva, tamanho_uniforme, tamanho_mascara,
                                         created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data["matricula"].strip().upper(),
                data["nome"].strip(),
                data.get("cpf", "").strip(),
                data["cargo"].strip(),
                depto,
                data.get("data_admissao", "").strip() or None,
                data.get("status", "Ativo"),
                data.get("observacoes", "").strip(),
                data.get("telefone", "").strip(),
                data.get("tamanho_calcado", "-").strip(),
                data.get("tamanho_luva", "-").strip(),
                data.get("tamanho_uniforme", "-").strip(),
                data.get("tamanho_mascara", "-").strip(),
                now
            ))
            conn.commit()
            return cursor.lastrowid

    @staticmethod
    def update_status(func_id, status):
        """Atualiza rapidamente apenas o status de um funcionário."""
        with get_connection() as conn:
            conn.execute("UPDATE funcionarios SET status = ? WHERE id = ?;", (status, func_id))
            conn.commit()
            return True

    @staticmethod
    def update_employee(func_id, data):
        """Atualiza dados do funcionário. Suporta dicionários parciais com segurança."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with get_connection() as conn:
            cur_row = conn.execute("SELECT * FROM funcionarios WHERE id = ?", (func_id,)).fetchone()
            cur = dict(cur_row) if cur_row else {}

            depto = (data.get("departamento") if "departamento" in data else cur.get("departamento") or "Geral").strip()
            conn.execute("INSERT OR IGNORE INTO departamentos (nome, descricao, created_at) VALUES (?, ?, ?);",
                         (depto, f"Setor {depto}", now))

            matricula = (data.get("matricula") if "matricula" in data else cur.get("matricula", "")).strip().upper()
            nome = (data.get("nome") if "nome" in data else cur.get("nome", "")).strip()
            cpf = (data.get("cpf") if "cpf" in data else cur.get("cpf", "")).strip()
            cargo = (data.get("cargo") if "cargo" in data else cur.get("cargo", "")).strip()
            data_adm = data.get("data_admissao") if "data_admissao" in data else cur.get("data_admissao")
            data_adm = (data_adm or "").strip() or None
            status = data.get("status") if "status" in data else cur.get("status", "Ativo")
            obs = (data.get("observacoes") if "observacoes" in data else cur.get("observacoes", "")).strip()
            tel = (data.get("telefone") if "telefone" in data else cur.get("telefone", "")).strip()
            tam_calc = (data.get("tamanho_calcado") if "tamanho_calcado" in data else cur.get("tamanho_calcado", "-")).strip()
            tam_luva = (data.get("tamanho_luva") if "tamanho_luva" in data else cur.get("tamanho_luva", "-")).strip()
            tam_uni = (data.get("tamanho_uniforme") if "tamanho_uniforme" in data else cur.get("tamanho_uniforme", "-")).strip()
            tam_masc = (data.get("tamanho_mascara") if "tamanho_mascara" in data else cur.get("tamanho_mascara", "-")).strip()

            conn.execute("""
                UPDATE funcionarios
                SET matricula = ?, nome = ?, cpf = ?, cargo = ?, departamento = ?,
                    data_admissao = ?, status = ?, observacoes = ?, telefone = ?,
                    tamanho_calcado = ?, tamanho_luva = ?, tamanho_uniforme = ?, tamanho_mascara = ?
                WHERE id = ?
            """, (
                matricula,
                nome,
                cpf,
                cargo,
                depto,
                data_adm,
                status,
                obs,
                tel,
                tam_calc,
                tam_luva,
                tam_uni,
                tam_masc,
                func_id
            ))
            conn.commit()
            return True

    @staticmethod
    def list_departamentos():
        """Retorna lista de departamentos com total de colaboradores e gastos totais com EPIs."""
        query = """
            SELECT d.id, d.nome, d.descricao,
                   (SELECT COUNT(*) FROM funcionarios f WHERE UPPER(f.departamento) = UPPER(d.nome)) as total_funcionarios,
                   (SELECT COUNT(*) FROM funcionarios f WHERE UPPER(f.departamento) = UPPER(d.nome) AND f.status = 'Ativo') as total_ativos,
                   COALESCE((
                       SELECT SUM(m.custo_total)
                       FROM movimentacoes m
                       JOIN funcionarios f ON m.funcionario_id = f.id
                       WHERE UPPER(f.departamento) = UPPER(d.nome) AND m.tipo = 'SAIDA'
                   ), 0.0) as total_gasto
            FROM departamentos d
            ORDER BY d.nome ASC;
        """
        with get_connection() as conn:
            rows = conn.execute(query).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def list_nomes_departamentos():
        """Retorna lista de nomes dos departamentos para ComboBox."""
        with get_connection() as conn:
            rows = conn.execute("SELECT nome FROM departamentos ORDER BY nome ASC;").fetchall()
            deptos = [r[0] for r in rows]
            if not deptos:
                deptos = [
                    "Linha de Montagem", "Manutenção Industrial", "Logística e Expedição",
                    "Operacional / Produção", "Segurança do Trabalho (SST)", "Qualidade / Laboratório",
                    "Administrativo / RH", "Obras / Serviços Externos"
                ]
            return deptos

    @staticmethod
    def create_departamento(nome, descricao=""):
        nome_clean = (nome or "").strip()
        if not nome_clean:
            raise ValueError("O nome do departamento não pode ser vazio!")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO departamentos (nome, descricao, created_at) VALUES (?, ?, ?);",
                (nome_clean, descricao.strip() or f"Setor {nome_clean}", now)
            )
            conn.commit()
            return True

    @staticmethod
    def delete_departamento(nome):
        with get_connection() as conn:
            conn.execute("DELETE FROM departamentos WHERE UPPER(nome) = UPPER(?);", (nome.strip(),))
            conn.commit()
            return True

    @staticmethod
    def resolve_delivered_size(row):
        """
        Resolve e retorna exclusivamente o tamanho unitário entregue ao colaborador.
        Nunca retorna lista de múltiplos tamanhos/grades (ex: '38, 39, 40, 41').
        """
        raw_tam = str(row.get("mov_tamanho") or row.get("tamanho") or "").strip()
        cat_tam = str(row.get("epi_tamanho_catalogo") or row.get("epi_tamanho") or "").strip()

        has_comma_raw = "," in raw_tam
        has_comma_cat = "," in cat_tam

        # Se o tamanho gravado no movimento for um tamanho específico (não vazio, sem vírgula, e não 'Único' caso o catálogo tenha opções)
        if raw_tam and not has_comma_raw and raw_tam.upper() not in ("ÚNICO", "UNICO", "-", ""):
            return raw_tam

        # Se raw_tam tiver vírgula ou for genérico/vazio, precisamos extrair os tamanhos candidatos
        if has_comma_raw:
            candidates = [c.strip() for c in raw_tam.split(",") if c.strip()]
        elif has_comma_cat:
            candidates = [c.strip() for c in cat_tam.split(",") if c.strip()]
        elif cat_tam and cat_tam.upper() not in ("ÚNICO", "UNICO", "-", ""):
            return cat_tam
        else:
            return raw_tam or cat_tam or "Único"

        # Tenta casar com o tamanho corporal do colaborador cadastrado
        nome_epi = (row.get("epi_nome") or "").upper()
        c_calc = str(row.get("tamanho_calcado") or "").strip()
        c_luva = str(row.get("tamanho_luva") or "").strip()
        c_uni = str(row.get("tamanho_uniforme") or "").strip()
        c_masc = str(row.get("tamanho_mascara") or "").strip()

        # Calçados e botas
        if any(k in nome_epi for k in ["BOTA", "BOTINA", "CALÇADO", "CALCADO", "SAPATO", "TÊNIS", "TENIS"]):
            if c_calc and c_calc not in ("-", ""):
                for c in candidates:
                    if c.upper() == c_calc.upper():
                        return c

        # Luvas
        if "LUVA" in nome_epi:
            if c_luva and c_luva not in ("-", ""):
                for c in candidates:
                    if c.upper() == c_luva.upper():
                        return c

        # Uniformes, vestimentas, toucas, meias, perneiras
        if any(k in nome_epi for k in ["UNIFORME", "CALÇA", "CALCA", "CAMISA", "CAMISETA", "JALECO", "MOLETON", "VEST", "AVENTAL", "CAPA", "MEIA", "MEIÃO", "TOUCA"]):
            if c_uni and c_uni not in ("-", ""):
                for c in candidates:
                    if c.upper() == c_uni.upper():
                        return c

        # Máscaras e respiradores
        if any(k in nome_epi for k in ["MÁSCARA", "MASCARA", "RESPIRADOR", "FACIAL"]):
            if c_masc and c_masc not in ("-", ""):
                for c in candidates:
                    if c.upper() == c_masc.upper():
                        return c

        # Tenta match em qualquer uma das medidas do colaborador
        for med in [c_calc, c_luva, c_uni, c_masc]:
            if med and med not in ("-", ""):
                for c in candidates:
                    if c.upper() == med.upper():
                        return c

        # Tenta verificar se na observação do movimento há o tamanho citado (ex: "Tam 42", "Tamanho G")
        obs = (row.get("observacao") or "").upper()
        if obs:
            for c in candidates:
                if f"TAM {c.upper()}" in obs or f"TAMANHO {c.upper()}" in obs or f" {c.upper()} " in f" {obs} ":
                    return c

        # Se raw_tam já era 'Único' e nenhuma grade específica pôde ser deduzida:
        if raw_tam and raw_tam.upper() not in ("-", "") and not has_comma_raw:
            return raw_tam

        # Fallback de segurança: se o catálogo tiver apenas 1 tamanho disponível, retorna ele.
        # Se houver múltiplos tamanhos e nenhum foi selecionado nem bateu com o colaborador, mantém 'Único' ou o gravado.
        # NUNCA chuta 'P' ou o primeiro tamanho arbitrariamente!
        if len(candidates) == 1:
            return candidates[0]

        return raw_tam if (raw_tam and not has_comma_raw) else "Único"

    @staticmethod
    def get_employee_sheet(func_id):
        """
        Retorna a ficha completa de EPIs do funcionário:
        todos os EPIs entregues, data, quem entregou, CA, quantidade e motivo.
        Garante que apenas o tamanho específico entregue ao colaborador seja exibido,
        e não a lista com todas as variações/grades cadastradas no sistema.
        """
        query = """
            SELECT m.id, m.tipo, m.quantidade, m.data_hora, m.responsavel_entrega,
                   m.motivo, m.observacao, m.assinatura_path, m.foto_path,
                   m.tamanho as mov_tamanho, m.estado_conservacao as mov_estado,
                   m.custo_unitario, m.custo_total,
                   e.id as epi_id, e.codigo as epi_codigo, e.nome as epi_nome, e.ca as epi_ca,
                   e.fabricante as epi_fabricante, e.tamanho as epi_tamanho_catalogo, e.unidade as epi_unidade,
                   COALESCE(e.preco_unitario, 0.0) as epi_preco,
                   COALESCE(e.preco_usado, ROUND(e.preco_unitario * 0.5, 2), 0.0) as epi_preco_usado,
                   COALESCE(e.dias_vida_util, 90) as dias_vida_util, e.validade_ca,
                   f.tamanho_calcado, f.tamanho_luva, f.tamanho_uniforme, f.tamanho_mascara
            FROM movimentacoes m
            JOIN epis e ON m.epi_id = e.id
            LEFT JOIN funcionarios f ON m.funcionario_id = f.id
            WHERE m.funcionario_id = ?
            ORDER BY m.data_hora ASC, m.id ASC
        """
        with get_connection() as conn:
            rows = conn.execute(query, (func_id,)).fetchall()
            items = []
            for r in rows:
                item = dict(r)
                single_tam = EmployeeService.resolve_delivered_size(item)
                item["tamanho"] = single_tam
                item["epi_tamanho"] = single_tam  # Mantém retrocompatibilidade transparente
                custo_u = item.get("custo_unitario")
                if custo_u is not None and float(custo_u) > 0:
                    val_u = float(custo_u)
                else:
                    mov_est = str(item.get("mov_estado") or "").upper()
                    if any(k in mov_est for k in ["USADO", "REUTIL", "BOM", "HIGIEN"]):
                        val_u = float(item.get("epi_preco_usado") or (float(item.get("epi_preco") or 0.0) * 0.5))
                    else:
                        val_u = float(item.get("epi_preco") or 0.0)
                item["valor_unitario"] = val_u
                item["valor_total"] = float(item.get("custo_total") or (val_u * item.get("quantidade", 1)))
                items.append(item)
            return items

    @staticmethod
    def get_summary():
        with get_connection() as conn:
            total = conn.execute("SELECT COUNT(*) FROM funcionarios").fetchone()[0]
            ativos = conn.execute("SELECT COUNT(*) FROM funcionarios WHERE status = 'Ativo'").fetchone()[0]
            return {"total": total, "ativos": ativos}
