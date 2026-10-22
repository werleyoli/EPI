import sys
import os

# Adiciona o diretório do projeto ao sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from database import init_db, APP_DIR, DB_FILE, EXPORTS_DIR
from ui.app import MainWindow

def main():
    # Garante criação das pastas necessárias no diretório do app
    os.makedirs(os.path.join(APP_DIR, "data"), exist_ok=True)
    os.makedirs(EXPORTS_DIR, exist_ok=True)

    # Inicializa banco de dados
    init_db()

    # Inicia a aplicação Desktop
    app = MainWindow()
    app.mainloop()

if __name__ == "__main__":
    main()
