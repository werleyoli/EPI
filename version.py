"""
Definição centralizada da versão e informações de release do EPI Master Pro.
"""

APP_NAME = "EPI Master Pro"
VERSION = "3.6.3"
BUILD_DATE = "22/10/2026"
RELEASE_TAG = "v3.6.3 - Identificação Visual de Produto Novo e Usado na Ficha e PDF (NR-6)"

def get_version_string():
    """Retorna texto de versão para a barra de status / rodapé."""
    return f"Versão {VERSION} - Portátil"

def get_full_version():
    """Retorna nome completo e versão do sistema."""
    return f"{APP_NAME} v{VERSION} ({BUILD_DATE})"
