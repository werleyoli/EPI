import os
import shutil
import zipfile
from datetime import datetime
from database import APP_DIR, DB_FILE, EXPORTS_DIR, get_connection

BACKUPS_DIR = os.path.join(APP_DIR, "backups")

class BackupService:
    @staticmethod
    def get_backup_dir():
        os.makedirs(BACKUPS_DIR, exist_ok=True)
        return BACKUPS_DIR

    @staticmethod
    def create_backup(dest_folder=None):
        """
        Gera um arquivo .zip com cópia segura do banco SQLite e de todas as pastas de exportações e assinaturas.
        """
        BackupService.get_backup_dir()
        target_dir = dest_folder if (dest_folder and os.path.isdir(dest_folder)) else BACKUPS_DIR

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"Backup_EPI_Master_Pro_{timestamp}.zip"
        zip_path = os.path.join(target_dir, filename)

        # Força checkpoint no SQLite antes de compactar para garantir consistência
        try:
            with get_connection() as conn:
                conn.execute("PRAGMA wal_checkpoint(FULL);")
        except Exception:
            pass

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 1. Banco de Dados
            if os.path.exists(DB_FILE):
                zipf.write(DB_FILE, arcname="data/epi_controle.db")

            # 2. Pasta de exportações e assinaturas
            if os.path.exists(EXPORTS_DIR):
                for root, _, files in os.walk(EXPORTS_DIR):
                    for file in files:
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, APP_DIR)
                        zipf.write(full_path, arcname=rel_path)

        from services.audit_service import AuditService
        AuditService.log(
            acao="BACKUP_CRIADO",
            modulo="SISTEMA",
            detalhes=f"Backup de segurança gerado em {zip_path}"
        )

        return zip_path

    @staticmethod
    def list_backups():
        """Lista os backups existentes na pasta padrão ordenados do mais recente ao mais antigo."""
        b_dir = BackupService.get_backup_dir()
        backups = []
        for f in os.listdir(b_dir):
            if f.endswith(".zip") and f.startswith("Backup_EPI_Master_Pro_"):
                fpath = os.path.join(b_dir, f)
                stat = os.stat(fpath)
                size_mb = round(stat.st_size / (1024 * 1024), 2)
                dt_str = datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y %H:%M:%S")
                backups.append({
                    "filename": f,
                    "filepath": fpath,
                    "size_mb": size_mb,
                    "date": dt_str,
                    "mtime": stat.st_mtime
                })
        backups.sort(key=lambda x: x["mtime"], reverse=True)
        return backups

    @staticmethod
    def restore_backup(zip_path):
        """
        Restaura o banco de dados e arquivos a partir de um arquivo .zip de backup.
        Cria automaticamente uma cópia de segurança prévia antes de substituir.
        """
        if not os.path.exists(zip_path) or not zipfile.is_zipfile(zip_path):
            raise ValueError("Arquivo de backup inválido ou não encontrado!")

        with zipfile.ZipFile(zip_path, 'r') as zipf:
            namelist = zipf.namelist()
            if "data/epi_controle.db" not in namelist:
                raise ValueError("O arquivo selecionado não contém a estrutura de banco de dados do EPI Master Pro!")

            # 1. Faz backup de segurança do estado atual antes da restauração
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safety_backup_db = os.path.join(APP_DIR, "data", f"epi_controle_pre_restore_{timestamp}.db.bak")
            if os.path.exists(DB_FILE):
                shutil.copy2(DB_FILE, safety_backup_db)

            # 2. Extrai os arquivos substituindo os atuais
            for member in namelist:
                target_path = os.path.join(APP_DIR, member)
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                with zipf.open(member) as source, open(target_path, "wb") as target:
                    shutil.copyfileobj(source, target)

        from services.audit_service import AuditService
        AuditService.log(
            acao="BACKUP_RESTAURADO",
            modulo="SISTEMA",
            detalhes=f"Restauração executada a partir de {zip_path}"
        )

        return True
