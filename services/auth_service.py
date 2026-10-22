from database import get_connection, hash_password
from datetime import datetime

class AuthService:
    _current_user = None

    @classmethod
    def set_current_user(cls, user_dict):
        cls._current_user = user_dict

    @classmethod
    def get_current_user(cls):
        if not cls._current_user:
            # Retorna usuário padrão se login não for obrigatório
            return {
                "id": 1,
                "username": "admin",
                "nome": "Administrador",
                "cargo": "Engenheiro de Segurança",
                "perfil": "ADMIN"
            }
        return cls._current_user

    @classmethod
    def is_admin(cls):
        user = cls.get_current_user()
        return user.get("perfil") == "ADMIN"

    @staticmethod
    def authenticate(username, password):
        """Verifica credenciais e retorna o usuário ou None."""
        pwd_hash = hash_password(password)
        with get_connection() as conn:
            row = conn.execute("""
                SELECT id, username, nome, cargo, perfil
                FROM usuarios_sistema
                WHERE username = ? AND password_hash = ? AND ativo = 1
            """, (username.strip().lower(), pwd_hash)).fetchone()

            if row:
                user = dict(row)
                AuthService.set_current_user(user)
                return user
            return None

    @staticmethod
    def list_users():
        with get_connection() as conn:
            rows = conn.execute("SELECT id, username, nome, cargo, perfil, ativo, created_at FROM usuarios_sistema ORDER BY nome ASC").fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def create_user(username, password, nome, cargo, perfil):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        pwd_hash = hash_password(password)
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO usuarios_sistema (username, password_hash, nome, cargo, perfil, ativo, created_at)
                VALUES (?, ?, ?, ?, ?, 1, ?)
            """, (username.strip().lower(), pwd_hash, nome.strip(), cargo.strip(), perfil.strip().upper(), now))
            conn.commit()
            return cursor.lastrowid

    @staticmethod
    def update_password(user_id, new_password):
        pwd_hash = hash_password(new_password)
        with get_connection() as conn:
            conn.execute("UPDATE usuarios_sistema SET password_hash = ? WHERE id = ?", (pwd_hash, user_id))
            conn.commit()
