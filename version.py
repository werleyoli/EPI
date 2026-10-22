"""
Definição centralizada da versão e informações de release do EPI Master Pro.
"""

APP_NAME = "EPI Master Pro"
VERSION = "3.6.4"
BUILD_DATE = "22/10/2026"
RELEASE_TAG = "v3.6.4 - Sincronização Dinâmica de Custos no Dashboard, Extrato e Relatório de Retidos + Filtro de Inativos na Ficha NR-6"

def get_version_string():
    """Retorna texto de versão para a barra de status / rodapé."""
    return f"Versão {VERSION} - Portátil"

def get_full_version():
    """Retorna nome completo e versão do sistema."""
    return f"{APP_NAME} v{VERSION} ({BUILD_DATE})"
