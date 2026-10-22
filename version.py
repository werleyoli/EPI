"""
Definição centralizada da versão e informações de release do EPI Master Pro.
"""

APP_NAME = "EPI Master Pro"
VERSION = "3.6.2"
BUILD_DATE = "22/10/2026"
RELEASE_TAG = "v3.6.2 - Ordenação Cronológica de Saídas na Ficha (Cima para Baixo), Preço Duplo e Validade Dinâmica"

def get_version_string():
    """Retorna texto de versão para a barra de status / rodapé."""
    return f"Versão {VERSION} - Portátil"

def get_full_version():
    """Retorna nome completo e versão do sistema."""
    return f"{APP_NAME} v{VERSION} ({BUILD_DATE})"
