from database import get_connection
from datetime import datetime
from services.movement_service import MovementService
from services.employee_service import EmployeeService

class MatrizService:
    @staticmethod
    def list_cargos():
        """Retorna lista de todos os cargos distintos de funcionários cadastrados e da matriz."""
        with get_connection() as conn:
            rows_f = conn.execute("SELECT DISTINCT cargo FROM funcionarios").fetchall()
            rows_m = conn.execute("SELECT DISTINCT cargo FROM matriz_cargos_epis").fetchall()
            cargos = sorted(list(set([r[0] for r in rows_f + rows_m if r[0]])))
            return cargos

    @staticmethod
    def get_epis_for_cargo(cargo):
        """Retorna todos os EPIs cadastrados para um cargo específico."""
        query = """
            SELECT m.id as matriz_id, m.cargo, m.quantidade as qtd_recomendada,
                   m.obrigatorio, m.periodicidade_dias,
                   e.id as epi_id, e.codigo, e.nome, e.ca, e.unidade, e.quantidade as saldo_atual,
                   e.preco_unitario, e.dias_vida_util
            FROM matriz_cargos_epis m
            JOIN epis e ON m.epi_id = e.id
            WHERE m.cargo = ? AND e.ativo = 1
            ORDER BY e.nome ASC
        """
        with get_connection() as conn:
            rows = conn.execute(query, (cargo,)).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def add_epi_to_cargo(cargo, epi_id, quantidade=1, periodicidade_dias=90):
        with get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO matriz_cargos_epis (cargo, epi_id, quantidade, obrigatorio, periodicidade_dias)
                VALUES (?, ?, ?, 1, ?)
            """, (cargo.strip(), epi_id, int(quantidade), int(periodicidade_dias)))
            conn.commit()

    @staticmethod
    def remove_epi_from_cargo(cargo, epi_id):
        with get_connection() as conn:
            conn.execute("DELETE FROM matriz_cargos_epis WHERE cargo = ? AND epi_id = ?", (cargo, epi_id))
            conn.commit()

    @staticmethod
    def deliver_full_kit(funcionario_id, responsavel, motivo="Entrega de Kit por Função (NR-6)",
                         assinatura_path=None, observacao="", data_hora=None,
                         is_retroativo=False, descontar_estoque=True):
        """
        Entrega o kit completo de EPIs vinculados ao cargo do colaborador em lote.
        Valida estoque de todos os itens antes de debitar (salvo em modo retroativo).
        """
        func = EmployeeService.get_employee(funcionario_id)
        if not func:
            raise ValueError("Funcionário não encontrado!")

        kit = MatrizService.get_epis_for_cargo(func["cargo"])
        if not kit:
            raise ValueError(f"Não há kit de EPIs configurado para a função '{func['cargo']}'.")

        # 1. Validação de estoque para todos os itens do kit
        if descontar_estoque and not is_retroativo:
            faltando = []
            for item in kit:
                if item["saldo_atual"] < item["qtd_recomendada"]:
                    faltando.append(f"{item['nome']} (Saldo: {item['saldo_atual']}, Requerido: {item['qtd_recomendada']})")

            if faltando:
                raise ValueError("Saldo insuficiente para entregar o kit completo:\n" + "\n".join(faltando))

        # 2. Executa saídas em lote com mesma data/hora e assinatura
        dt_final = data_hora or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        mov_ids = []

        for item in kit:
            tam_item = "Único"
            try:
                from services.epi_service import EPIService
                grades = EPIService.get_available_sizes(item["epi_id"])
                sizes = [g["tamanho"] for g in grades if g.get("tamanho")]
                dummy_row = {
                    "epi_nome": item.get("nome", ""),
                    "tamanho_calcado": func.get("tamanho_calcado"),
                    "tamanho_luva": func.get("tamanho_luva"),
                    "tamanho_uniforme": func.get("tamanho_uniforme"),
                    "tamanho_mascara": func.get("tamanho_mascara"),
                    "epi_tamanho_catalogo": ", ".join(sizes) if sizes else ""
                }
                tam_item = EmployeeService.resolve_delivered_size(dummy_row)
            except Exception:
                tam_item = "Único"

            m_id = MovementService.register_exit(
                epi_id=item["epi_id"],
                funcionario_id=funcionario_id,
                quantidade=item["qtd_recomendada"],
                responsavel_entrega=responsavel,
                motivo=motivo,
                data_hora=dt_final,
                observacao=f"Kit do Cargo: {func['cargo']}. {observacao}".strip(),
                assinatura_path=assinatura_path,
                is_retroativo=is_retroativo,
                descontar_estoque=descontar_estoque,
                tamanho=tam_item
            )
            mov_ids.append(m_id)

        return mov_ids
