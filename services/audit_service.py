from database import get_connection
from datetime import datetime
from services.auth_service import AuthService

class AuditService:
    @staticmethod
    def log(acao: str, modulo: str, detalhes: str = ""):
        """Registra uma ação no log de auditoria com usuário atual e timestamp."""
        try:
            cur_user = AuthService.get_current_user()
            usuario_nome = cur_user.get("nome", "Sistema")
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            with get_connection() as conn:
                conn.execute("""
                    INSERT INTO logs_auditoria (usuario_nome, acao, modulo, detalhes, data_hora)
                    VALUES (?, ?, ?, ?, ?);
                """, (usuario_nome, acao, modulo, detalhes, now))
                conn.commit()
        except Exception as e:
            print(f"Erro ao registrar auditoria: {e}")

    @staticmethod
    def list_logs(search="", modulo=None, limit=200):
        """Retorna os registros de auditoria mais recentes com filtros opcionais."""
        query = "SELECT id, usuario_nome, acao, modulo, detalhes, data_hora FROM logs_auditoria WHERE 1=1"
        params = []

        if modulo and modulo != "TODOS":
            query += " AND modulo = ?"
            params.append(modulo)

        if search:
            query += " AND (usuario_nome LIKE ? OR acao LIKE ? OR detalhes LIKE ?)"
            s = f"%{search.strip()}%"
            params.extend([s, s, s])

        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        with get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]
