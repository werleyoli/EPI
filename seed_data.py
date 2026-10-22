from database import init_db, get_connection
from services.epi_service import EPIService
from services.employee_service import EmployeeService
from services.movement_service import MovementService
from datetime import datetime, timedelta

def seed_sample_data():
    """Popula e atualiza o banco de dados com dados realistas de teste."""
    init_db()

    with get_connection() as conn:
        cursor = conn.cursor()

        # Atualiza preços unitários e vidas úteis dos EPIs já cadastrados caso estejam zerados
        updates = [
            ("EPI-001", 38.50, 365), # Capacete
            ("EPI-002", 14.90, 90),  # Óculos
            ("EPI-003", 2.80, 30),   # Plug silicone
            ("EPI-004", 26.00, 45),  # Luva vaqueta
            ("EPI-005", 125.00, 180),# Botina
            ("EPI-006", 4.50, 15),   # PFF2
        ]
        for cod, preco, dias in updates:
            cursor.execute("""
                UPDATE epis 
                SET preco_unitario = ?, dias_vida_util = ?
                WHERE codigo = ? AND (preco_unitario = 0 OR preco_unitario IS NULL)
            """, (preco, dias, cod))

        # Popula matriz de EPIs por Cargo se estiver vazia
        cursor.execute("SELECT COUNT(*) FROM matriz_cargos_epis;")
        if cursor.fetchone()[0] == 0:
            epis_map = {r["codigo"]: r["id"] for r in cursor.execute("SELECT codigo, id FROM epis").fetchall()}
            
            matriz_dados = [
                # Mecânico de Manutenção
                ("Mecânico de Manutenção", "EPI-001", 1, 1, 365),
                ("Mecânico de Manutenção", "EPI-002", 1, 1, 90),
                ("Mecânico de Manutenção", "EPI-003", 2, 1, 30),
                ("Mecânico de Manutenção", "EPI-004", 1, 1, 45),
                ("Mecânico de Manutenção", "EPI-005", 1, 1, 180),

                # Operadora de Produção / Operador de Produção
                ("Operadora de Produção", "EPI-002", 1, 1, 90),
                ("Operadora de Produção", "EPI-003", 2, 1, 30),
                ("Operadora de Produção", "EPI-004", 1, 1, 45),

                # Operador de Empilhadeira
                ("Operador de Empilhadeira", "EPI-001", 1, 1, 365),
                ("Operador de Empilhadeira", "EPI-002", 1, 1, 90),
                ("Operador de Empilhadeira", "EPI-005", 1, 1, 180),

                # Eletricista Industrial
                ("Eletricista Industrial", "EPI-001", 1, 1, 365),
                ("Eletricista Industrial", "EPI-002", 1, 1, 90),
                ("Eletricista Industrial", "EPI-005", 1, 1, 180),
            ]

            for cargo, cod, qtd, obg, dias in matriz_dados:
                if cod in epis_map:
                    cursor.execute("""
                        INSERT OR IGNORE INTO matriz_cargos_epis (cargo, epi_id, quantidade, obrigatorio, periodicidade_dias)
                        VALUES (?, ?, ?, ?, ?)
                    """, (cargo, epis_map[cod], qtd, obg, dias))

        conn.commit()

if __name__ == "__main__":
    seed_sample_data()
    print("Dados e Matriz de Cargos atualizados com sucesso!")
