import os
import sys
import subprocess
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def build_executable():
    try:
        from version import get_full_version
        v_title = get_full_version().upper()
    except Exception:
        v_title = "EPI MASTER PRO"

    print("=========================================================")
    print(f"   INICIANDO COMPILAÇÃO DO EXECUTÁVEL: {v_title}     ")
    print("=========================================================")

    # Garante que a pasta data e exports existem
    os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "exports"), exist_ok=True)

    # Comando do PyInstaller
    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name", "EPI_Master_Pro",
        "--collect-all", "customtkinter",
        "--collect-all", "reportlab",
        "--collect-all", "qrcode",
        "--collect-all", "cv2",
        "--hidden-import", "sqlite3",
        "--hidden-import", "pandas",
        "--hidden-import", "openpyxl",
        "--hidden-import", "PIL",
        "--hidden-import", "qrcode",
        "--hidden-import", "cv2",
        "--hidden-import", "services",
        "--hidden-import", "ui",
        "--hidden-import", "version",
        "main.py"
    ]

    print("\nExecutando PyInstaller com as dependências completas...")
    result = subprocess.run(cmd, cwd=BASE_DIR)

    if result.returncode == 0:
        dist_dir = os.path.join(BASE_DIR, "dist", "EPI_Master_Pro")
        os.makedirs(os.path.join(dist_dir, "data"), exist_ok=True)
        os.makedirs(os.path.join(dist_dir, "exports"), exist_ok=True)
        os.makedirs(os.path.join(dist_dir, "exports", "photos"), exist_ok=True)

        for db_name in ["epi_control.db", "epi_controle.db"]:
            db_src = os.path.join(BASE_DIR, "data", db_name)
            db_dst = os.path.join(dist_dir, "data", db_name)
            if os.path.exists(db_src):
                try:
                    shutil.copy2(db_src, db_dst)
                except Exception:
                    pass

        sig_src = os.path.join(BASE_DIR, "data", "signatures")
        sig_dst = os.path.join(dist_dir, "data", "signatures")
        if os.path.exists(sig_src):
            try:
                shutil.copytree(sig_src, sig_dst, dirs_exist_ok=True)
            except Exception:
                pass

        exe_path = os.path.join(dist_dir, "EPI_Master_Pro.exe")
        print("\n=========================================================")
        print("[SUCESSO] EXECUTAVEL CRIADO COM SUCESSO!")
        print(f"Caminho do Executavel:\n{exe_path}")
        print("=========================================================")
        return True
    else:
        print("\nErro durante a compilação!")
        return False

if __name__ == "__main__":
    build_executable()
